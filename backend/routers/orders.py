from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from backend.database import User, ApprovalRequest, Transaction, SpendingLimit
from backend.auth import get_current_user, get_db
from backend.schemas import (
    ApprovalRequestResponse, TransactionDetail, 
    TransactionSchema, PaymentIntentSchema
)
from backend.agents.checkout import CheckoutService
from typing import List

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/request-approval", response_model=ApprovalRequestResponse)
def request_purchase_approval(details: TransactionDetail, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Check Spending Limits
    limits = current_user.spending_limits
    if limits:
        if details.total > limits.per_transaction_limit:
            raise HTTPException(status_code=400, detail=f"Transaction exceed per-transaction limit of {limits.per_transaction_limit}")
        if (limits.daily_spent + details.total) > limits.daily_limit:
            raise HTTPException(status_code=400, detail=f"Transaction exceed daily limit of {limits.daily_limit}")

    # 2. Generate Approval Request (HITL)
    new_request = ApprovalRequest(
        user_id=current_user.id,
        transaction_details=details.dict(),
        reasoning=details.reasoning,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    # Trigger notification (stub)
    # send_notification(current_user.email, "Purchase Approval Required", details.dict())
    
    return new_request

@router.post("/approve/{request_id}")
def approve_transaction(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id, ApprovalRequest.user_id == current_user.id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {approval.status}")

    # 1. Execute "Purchase" (Stub)
    transaction_details = approval.transaction_details
    new_tx = Transaction(
        user_id=current_user.id,
        product_name=transaction_details["product"],
        merchant=transaction_details["merchant"],
        price=transaction_details["total"],
        status="completed"
    )
    db.add(new_tx)
    
    # 2. Update status and daily spend
    approval.status = "approved"
    if current_user.spending_limits:
        current_user.spending_limits.daily_spent += transaction_details["total"]
    
    db.commit()
    return {"message": "Transaction approved and executed"}

@router.post("/reject/{request_id}")
def reject_transaction(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id, ApprovalRequest.user_id == current_user.id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    approval.status = "rejected"
    db.commit()
    return {"message": "Transaction rejected"}

@router.get("/pending", response_model=List[ApprovalRequestResponse])
def get_pending_approvals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ApprovalRequest).filter(ApprovalRequest.user_id == current_user.id, ApprovalRequest.status == "pending").all()

@router.post("/confirm-payment/{session_id}", response_model=PaymentIntentSchema)
async def confirm_order_payment(
    session_id: str, 
    payment_method_id: str, 
    current_user: User = Depends(get_current_user)
):
    """
    Finalizes an order by processing the payment.
    Ideally called after the user approves a transaction request.
    """
    checkout_service = CheckoutService()
    try:
        payment_intent = await checkout_service.process_payment(
            session_id=session_id,
            payment_method_id=payment_method_id,
            user_id=str(current_user.id)
        )
        return payment_intent
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
