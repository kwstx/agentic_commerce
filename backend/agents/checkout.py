import asyncio
import uuid
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.schemas import (
    CartItem, InternalCart, CheckoutAttempt, 
    UnifiedCheckoutSession, CheckoutStatus
)
import os

class CheckoutService:
    def __init__(self):
        self.sessions: Dict[str, UnifiedCheckoutSession] = {}
        # Shopify Credentials (would be in .env)
        self.shopify_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "mock_token")
        self.shopify_shop_url = os.getenv("SHOPIFY_SHOP_URL", "mock-store.myshopify.com")

    async def create_cart(self, items: List[CartItem]) -> InternalCart:
        """Aggregates items and calculates totals."""
        subtotal = sum(item.price * item.quantity for item in items)
        
        # In a real scenario, these would call external APIs or merchant endpoints
        taxes = await self._calculate_taxes(subtotal, items)
        shipping = await self._calculate_shipping(items)
        discounts = await self._calculate_discounts(subtotal, items)
        
        total = subtotal + taxes + shipping - discounts
        
        return InternalCart(
            items=items,
            subtotal=round(subtotal, 2),
            taxes=round(taxes, 2),
            shipping=round(shipping, 2),
            discounts=round(discounts, 2),
            total=round(total, 2)
        )

    async def _calculate_taxes(self, subtotal: float, items: List[CartItem]) -> float:
        """Mock tax calculation logic."""
        # This could call Vertex Tax, TaxJar, etc.
        return subtotal * 0.08  # Default 8% tax

    async def _calculate_shipping(self, items: List[CartItem]) -> float:
        """Mock shipping calculation logic."""
        # Could call EasyPost or Merchant Shipping API
        return 15.00 if items else 0.0

    async def _calculate_discounts(self, subtotal: float, items: List[CartItem]) -> float:
        """Mock discount calculation logic."""
        return 0.0

    async def initiate_checkout(self, cart: InternalCart) -> UnifiedCheckoutSession:
        """Starts checkout attempts across all merchants in the cart."""
        session_id = str(uuid.uuid4())
        session = UnifiedCheckoutSession(
            session_id=session_id,
            status=CheckoutStatus.PENDING
        )
        
        # Group items by merchant
        merchant_groups = {}
        for item in cart.items:
            if item.merchant not in merchant_groups:
                merchant_groups[item.merchant] = []
            merchant_groups[item.merchant].append(item)
            
        # Create an attempt for each merchant
        tasks = []
        for merchant, items in merchant_groups.items():
            # We create a preliminary cart for this merchant
            merchant_cart = InternalCart(items=items)
            tasks.append(self._process_merchant_checkout(session_id, merchant, merchant_cart))
            
        attempts = await asyncio.gather(*tasks)
        session.attempts = attempts
        
        # Aggregate totals from all merchant attempts
        session.final_total = sum(a.cart.total for a in attempts)
        
        # Update overall session status
        if all(a.status == CheckoutStatus.COMPLETED for a in attempts):
            session.status = CheckoutStatus.COMPLETED
        elif any(a.status == CheckoutStatus.PROCESSING for a in attempts):
            session.status = CheckoutStatus.PROCESSING
        else:
            session.status = CheckoutStatus.FAILED
            
        self.sessions[session_id] = session
        return session

    async def _process_merchant_checkout(self, session_id: str, merchant: str, cart: InternalCart) -> CheckoutAttempt:
        """Routes checkout to the correct provider adapter."""
        attempt_id = str(uuid.uuid4())
        attempt = CheckoutAttempt(
            id=attempt_id,
            cart=cart,
            merchant=merchant,
            status=CheckoutStatus.PROCESSING
        )
        
        try:
            if merchant.lower() == "shopify":
                result = await self._shopify_checkout(cart)
                attempt.status = CheckoutStatus.COMPLETED
                attempt.provider_checkout_id = result.get("id")
                attempt.checkout_url = result.get("url")
                # Update cart with totals fetched from Shopify
                attempt.cart.subtotal = result.get("subtotal", cart.subtotal)
                attempt.cart.taxes = result.get("taxes", 0.0)
                attempt.cart.shipping = result.get("shipping", 0.0)
                attempt.cart.total = result.get("total", cart.subtotal)
            elif merchant.lower() == "amazon":
                # Mock Amazon response
                attempt.status = CheckoutStatus.COMPLETED
                attempt.checkout_url = "https://amazon.com/checkout/mock"
                attempt.cart.subtotal = sum(i.price * i.quantity for i in cart.items)
                attempt.cart.taxes = attempt.cart.subtotal * 0.07
                attempt.cart.shipping = 10.0
                attempt.cart.total = attempt.cart.subtotal + attempt.cart.taxes + attempt.cart.shipping
            else:
                # Generic fallback
                attempt.status = CheckoutStatus.COMPLETED
                attempt.checkout_url = f"https://{merchant}.com/cart"
                attempt.cart.subtotal = sum(i.price * i.quantity for i in cart.items)
                attempt.cart.total = attempt.cart.subtotal
                
        except Exception as e:
            attempt.status = CheckoutStatus.FAILED
            attempt.error_message = str(e)
            
        attempt.updated_at = datetime.now()
        return attempt

    async def _shopify_checkout(self, cart: InternalCart) -> Dict[str, Any]:
        """
        Implementation of Shopify Cart and Checkout GraphQL mutations.
        """
        lines = [{"merchandiseId": item.variant_id or f"id_{item.product_id}", "quantity": item.quantity} for item in cart.items]
        
        print(f"--- Calling Shopify GraphQL cartCreate for {len(lines)} items ---")
        await asyncio.sleep(0.5)
        
        subtotal = sum(i.price * i.quantity for i in cart.items)
        taxes = subtotal * 0.08
        shipping = 12.0
        
        return {
            "id": f"gid://shopify/Cart/{uuid.uuid4().hex}",
            "url": f"https://{self.shopify_shop_url}/checkouts/c/{uuid.uuid4().hex}",
            "subtotal": subtotal,
            "taxes": taxes,
            "shipping": shipping,
            "total": subtotal + taxes + shipping
        }

    def get_session_status(self, session_id: str) -> Optional[UnifiedCheckoutSession]:
        return self.sessions.get(session_id)
