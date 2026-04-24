from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from backend.database import User, UserPreference, SpendingLimit
from backend.auth import get_db, get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from backend.schemas import UserCreate, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Initialize default preferences/limits
    new_pref = UserPreference(user_id=new_user.id)
    new_pref.set_preferences({
        "budget_thresholds": {},
        "brand_affinities": [],
        "shipping_priorities": [],
        "ethical_filters": []
    })
    new_limits = SpendingLimit(user_id=new_user.id)
    db.add(new_pref)
    db.add(new_limits)
    db.commit()
    
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/passwordless/request")
async def request_passwordless(email: str, db: Session = Depends(get_db)):
    # Stub for sending magic link
    # In production, generate a short-lived token and email it to the user
    return {"message": "Magic link would be sent to " + email}

@router.get("/passwordless/callback")
async def passwordless_callback(token: str, db: Session = Depends(get_db)):
    # Stub for verifying magic link token and returning JWT
    return {"access_token": "...", "token_type": "bearer"}

@router.get("/oauth/google")
async def oauth_google():
    # Stub for Google OAuth2 redirect
    return {"url": "https://accounts.google.com/o/oauth2/v2/auth..."}
