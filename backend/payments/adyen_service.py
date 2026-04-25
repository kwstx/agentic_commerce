import Adyen
import os
from typing import Dict, Any
from backend.schemas import PaymentIntentSchema

class AdyenPaymentService:
    def __init__(self):
        self.adyen = Adyen.Adyen()
        self.adyen.payment.client_key = os.getenv("ADYEN_CLIENT_KEY")
        self.adyen.payment.xapi_key = os.getenv("ADYEN_API_KEY")
        self.adyen.platform = "test"  # or "live"
        self.merchant_account = os.getenv("ADYEN_MERCHANT_ACCOUNT")

    async def create_payment(self, amount: int, currency: str, payment_method: Dict[str, Any], reference: str) -> Dict[str, Any]:
        """
        Creates a payment using Adyen.
        """
        request = {
            "amount": {"value": amount, "currency": currency},
            "reference": reference,
            "paymentMethod": payment_method,
            "merchantAccount": self.merchant_account,
            "returnUrl": "https://your-app.com/checkout/callback"
        }
        
        result = self.adyen.checkout.payments(request)
        return result.message
