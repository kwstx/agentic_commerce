import stripe
import os
from typing import Optional, Dict, Any
from backend.schemas import PaymentIntentSchema, PaymentStatus
from backend.config import settings
from backend.payments.fraud import RiskAnalyzer

class StripePaymentService:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY.get_secret_value()
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET.get_secret_value()
        self.risk_analyzer = RiskAnalyzer()

    async def create_payment_intent(
        self, 
        amount: int, 
        currency: str, 
        payment_method_id: str, 
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentIntentSchema:
        """
        Creates a Stripe PaymentIntent with internal fraud checks.
        """
        # 1. Internal Fraud Check
        risk_score = await self.risk_analyzer.calculate_risk_score(user_id, amount)
        if risk_score > 0.8:
            raise Exception("Transaction flagged as high risk by internal anomaly detection.")

        # 2. Map metadata
        intent_metadata = metadata or {}
        intent_metadata.update({"user_id": user_id, "internal_risk_score": risk_score})

        # 3. Create Intent on Stripe
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                payment_method=payment_method_id,
                confirmation_method="manual",
                confirm=True,
                metadata=intent_metadata,
                # Enable Stripe radar/fraud checks
                fraud_details={"user_id": user_id} if user_id else {}
            )

            return PaymentIntentSchema(
                id=intent.id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                next_action=intent.next_action
            )
        except stripe.error.StripeError as e:
            # Audit log here
            print(f"Stripe Error: {str(e)}")
            raise e

    def construct_webhook_event(self, payload: str, sig_header: str):
        """Validates and constructs a Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")

    async def confirm_payment(self, payment_intent_id: str) -> PaymentIntentSchema:
        """Confirms a payment intent, handling 3D Secure if needed."""
        intent = stripe.PaymentIntent.confirm(payment_intent_id)
        return PaymentIntentSchema(
            id=intent.id,
            amount=intent.amount,
            currency=intent.currency,
            status=intent.status,
            client_secret=intent.client_secret,
            next_action=intent.next_action
        )
