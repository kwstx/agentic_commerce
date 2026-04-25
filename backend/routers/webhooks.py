from fastapi import APIRouter, Request, Header, HTTPException
from backend.payments.stripe_service import StripePaymentService
import stripe

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
stripe_service = StripePaymentService()

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Handles Stripe webhooks for payment status updates.
    """
    payload = await request.body()
    try:
        event = stripe_service.construct_webhook_event(payload.decode("utf-8"), stripe_signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        await handle_payment_success(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        await handle_payment_failure(payment_intent)
    elif event['type'] == 'payment_intent.processing':
        payment_intent = event['data']['object']
        # Handle processing state
        pass
    
    return {"status": "success"}

async def handle_payment_success(payment_intent):
    """Update internal order/checkout status to completed."""
    session_id = payment_intent.get('metadata', {}).get('session_id')
    print(f"Payment succeeded for session: {session_id}")
    # Logic to finalize order in database

async def handle_payment_failure(payment_intent):
    """Update internal order/checkout status to failed."""
    session_id = payment_intent.get('metadata', {}).get('session_id')
    error_message = payment_intent.get('last_payment_error', {}).get('message')
    print(f"Payment failed for session: {session_id}: {error_message}")
    # Logic to mark attempt as failed in database
