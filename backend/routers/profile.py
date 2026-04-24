from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import User, UserPreference, SpendingLimit, PaymentTokenVault
from backend.auth import get_current_user, get_db
from backend.schemas import PreferenceSchema, SpendingLimitSchema

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/preferences", response_model=PreferenceSchema)
def get_preferences(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return current_user.preferences.get_preferences()

@router.put("/preferences")
def update_preferences(pref_data: PreferenceSchema, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pref = current_user.preferences
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
    pref.set_preferences(pref_data.dict())
    db.commit()
    return {"message": "Preferences updated and encrypted"}

@router.get("/limits", response_model=SpendingLimitSchema)
def get_limits(current_user: User = Depends(get_current_user)):
    if not current_user.spending_limits:
        return {"per_transaction_limit": 100.0, "daily_limit": 500.0}
    return {
        "per_transaction_limit": current_user.spending_limits.per_transaction_limit,
        "daily_limit": current_user.spending_limits.daily_limit
    }

@router.put("/limits")
def update_limits(limits: SpendingLimitSchema, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lim = current_user.spending_limits
    if not lim:
        lim = SpendingLimit(user_id=current_user.id)
        db.add(lim)
    lim.per_transaction_limit = limits.per_transaction_limit
    lim.daily_limit = limits.daily_limit
    db.commit()
    return {"message": "Spending limits updated"}

@router.post("/payment/vault")
def vault_payment_token(provider: str, token_ref: str, last_four: str, card_type: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # In a real app, this would be the endpoint receiving the token from the provider
    new_token = PaymentTokenVault(
        user_id=current_user.id,
        provider=provider,
        token_reference=token_ref,
        last_four=last_four,
        card_type=card_type
    )
    db.add(new_token)
    db.commit()
    return {"message": "Payment token securely vaulted"}
