from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    text: str
    user_id: Optional[str] = "guest"

class Product(BaseModel):
    id: str
    name: str
    price: float
    rating: float
    shipping: str

class ChatResponse(BaseModel):
    text: str
    data: Optional[List[Product]] = None

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Preference Schemas
class PreferenceSchema(BaseModel):
    budget_thresholds: Dict[str, float]
    brand_affinities: List[str]
    shipping_priorities: List[str]
    ethical_filters: List[str]

# Consent Schemas
class SpendingLimitSchema(BaseModel):
    per_transaction_limit: float
    daily_limit: float

# Approval Schemas
class TransactionDetail(BaseModel):
    product: str
    merchant: str
    price: float
    taxes: float
    shipping_cost: float
    total: float
    reasoning: str

class ApprovalRequestResponse(BaseModel):
    id: int
    transaction_details: Dict[str, Any]
    reasoning: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class TransactionSchema(BaseModel):
    id: int
    product_name: str
    merchant: str
    price: float
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True
