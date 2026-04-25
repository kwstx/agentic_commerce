import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import AuditLog, Order, SessionLocal
from backend.agents.checkout import CheckoutService
from backend.schemas import CartItem, InternalCart, CheckoutStatus
import json

# Setup logging
logger = logging.getLogger(__name__)

class TransactionCoordinator:
    def __init__(self, db: Session, websocket_manager=None):
        self.db = db
        self.checkout_service = CheckoutService()
        self.ws_manager = websocket_manager

    async def _broadcast_status(self, user_id: str, message: str, data: Optional[Dict] = None):
        """Helper to send real-time updates."""
        if self.ws_manager:
            await self.ws_manager.send_personal_message(
                json.dumps({"type": "transaction_status", "message": message, "data": data or {}}),
                user_id
            )
        logger.info(f"Transaction Status [{user_id}]: {message}")

    async def _log_audit(self, user_id: str, transaction_id: str, step: str, action: str, 
                         decision: str, response: Any, status: str):
        """Immutable audit trail."""
        log_entry = AuditLog(
            user_id=user_id,
            transaction_id=transaction_id,
            step=step,
            action=action,
            decision=decision,
            api_response_summary=response if isinstance(response, dict) else {"msg": str(response)},
            status=status
        )
        self.db.add(log_entry)
        self.db.commit()

    async def execute_transaction(self, user_id: str, items: List[CartItem]) -> Dict[str, Any]:
        """
        Executes the full purchase sequence as an atomic workflow.
        Steps:
        1. Inventory Verification
        2. Address/Fraud Verification
        3. Merchant Cart Creation (Hold)
        4. Payment Processing
        5. Order Confirmation & Storage
        """
        transaction_id = f"tx_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        try:
            # 1. Start Workflow
            await self._broadcast_status(user_id, "Initializing transaction workflow...", {"tx_id": transaction_id})
            
            # --- STEP 1: Inventory Check ---
            await self._broadcast_status(user_id, "Verifying inventory availability...")
            inventory_verified = True # Logic would go here
            if not inventory_verified:
                raise Exception("Inventory no longer available for one or more items.")
            
            await self._log_audit(user_id, transaction_id, "inventory_check", "EXECUTE", 
                                "Verified availability across merchants", {"status": "available"}, "success")

            # --- STEP 2: Initiate Merchant Sessions (Holds) ---
            await self._broadcast_status(user_id, "Creating secure checkout sessions with merchants...")
            cart = await self.checkout_service.create_cart(items)
            session = await self.checkout_service.initiate_checkout(cart)
            
            if session.status == CheckoutStatus.FAILED:
                failed_merchants = [a.merchant for a in session.attempts if a.status == CheckoutStatus.FAILED]
                raise Exception(f"Failed to initiate checkout with merchants: {', '.join(failed_merchants)}")

            await self._log_audit(user_id, transaction_id, "merchant_initiation", "EXECUTE", 
                                f"Sessions created for {len(session.attempts)} merchants", 
                                [a.dict() for a in session.attempts], "success")

            # --- STEP 3: Payment Processing ---
            # NOTE: In a real flow, this might wait for a payment method from the vault or a secure redirect.
            # Assuming we have a payment_method_id for this user.
            await self._broadcast_status(user_id, "Processing payment...")
            
            # For demo purposes, we'll use a mock payment processing
            # In production, this calls checkout_service.process_payment
            payment_success = True 
            if not payment_success:
                raise Exception("Payment declined by provider.")

            await self._log_audit(user_id, transaction_id, "payment_processing", "EXECUTE", 
                                "Payment authorized successfully", {"status": "authorized"}, "success")

            # --- STEP 4: Finalize & Confirm ---
            await self._broadcast_status(user_id, "Confirming order with merchants...")
            
            # Create Order records
            orders = []
            for attempt in session.attempts:
                order = Order(
                    user_id=int(user_id),
                    transaction_id=transaction_id,
                    merchant=attempt.merchant,
                    items=[i.dict() for i in attempt.cart.items],
                    total_amount=attempt.cart.total,
                    confirmation_number=f"CONF_{attempt.id[:8].upper()}",
                    status="placed",
                    tracking_number=f"TRK_{attempt.id[:8].upper()}",
                    receipt_url=f"https://{attempt.merchant}.com/receipt/{attempt.id}"
                )
                self.db.add(order)
                orders.append(order)
            
            self.db.commit()
            
            await self._log_audit(user_id, transaction_id, "order_finalization", "EXECUTE", 
                                "Orders placed and recorded in history", {"order_count": len(orders)}, "success")
            
            await self._broadcast_status(user_id, "Transaction completed successfully!", {
                "tx_id": transaction_id,
                "orders": [{"merchant": o.merchant, "conf": o.confirmation_number} for o in orders]
            })

            return {
                "status": "success",
                "transaction_id": transaction_id,
                "orders": [
                    {
                        "merchant": o.merchant,
                        "confirmation": o.confirmation_number,
                        "tracking": o.tracking_number,
                        "receipt": o.receipt_url
                    } for o in orders
                ]
            }

        except Exception as e:
            await self._broadcast_status(user_id, f"Transaction failed: {str(e)}. Triggering rollback...")
            await self._handle_rollback(user_id, transaction_id, str(e))
            return {"status": "failed", "error": str(e), "transaction_id": transaction_id}

    async def _handle_rollback(self, user_id: str, transaction_id: str, failure_reason: str):
        """Compensating actions to release holds and notify user."""
        logger.warning(f"ROLLBACK for {transaction_id}: {failure_reason}")
        
        # 1. Log Rollback Attempt
        await self._log_audit(user_id, transaction_id, "rollback_orchestration", "ROLLBACK", 
                            f"Initiating compensation due to: {failure_reason}", 
                            {"reason": failure_reason}, "processing")

        # 2. Compensating Action: Release Merchant Holds
        # In a real system, this would call DELETE on merchant checkout sessions or cancel orders
        await self._broadcast_status(user_id, "Rolling back merchant checkout sessions...")
        # Mocking merchant cancellation calls
        await asyncio.sleep(1) 
        
        await self._log_audit(user_id, transaction_id, "merchant_cancellation", "ROLLBACK", 
                            "Sent cancellation requests to upstream merchants", {"status": "cancelled"}, "success")

        # 3. Compensating Action: Void Payment Auth (if applicable)
        await self._broadcast_status(user_id, "Voiding temporary payment holds...")
        # Mocking payment void
        
        await self._log_audit(user_id, transaction_id, "payment_void", "ROLLBACK", 
                            "Voided payment authorization", {"status": "voided"}, "success")

        await self._broadcast_status(user_id, "Rollback successful. Your cart has been cleared on merchants.")
