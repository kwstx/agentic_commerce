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

# Cart and Checkout Abstraction Schemas
class CartItem(BaseModel):
    product_id: str
    name: str
    quantity: int
    price: float
    merchant: str
    variant_id: Optional[str] = None
    currency: str = "USD"
    metadata: Dict[str, Any] = {}

class InternalCart(BaseModel):
    items: List[CartItem] = []
    subtotal: float = 0.0
    taxes: float = 0.0
    shipping: float = 0.0
    discounts: float = 0.0
    total: float = 0.0
    currency: str = "USD"

class CheckoutStatus(str):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

class CheckoutAttempt(BaseModel):
    id: str
    cart: InternalCart
    merchant: str
    status: str = "pending"
    provider_checkout_id: Optional[str] = None
    checkout_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class UnifiedCheckoutSession(BaseModel):
    session_id: str
    attempts: List[CheckoutAttempt] = []
    final_total: float = 0.0
    status: str = "pending"

# Payment Schemas
class PaymentMethodVaultItem(BaseModel):
    id: str
    provider: str  # 'stripe', 'adyen'
    last4: str
    brand: str
    expiry_month: int
    expiry_year: int
    is_default: bool = False

class PaymentIntentSchema(BaseModel):
    id: str
    amount: int  # in cents
    currency: str
    status: str
    client_secret: Optional[str] = None
    next_action: Optional[Dict[str, Any]] = None # For 3D Secure

class PaymentStatus(str):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    PROCESSING = "processing"
    REQUIRES_ACTION = "requires_action"
    CANCELED = "canceled"

class AuditLogSchema(BaseModel):
    step: str
    action: str
    decision: str
    api_response_summary: Dict[str, Any]
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True

class OrderSchema(BaseModel):
    id: int
    transaction_id: str
    merchant: str
    items: List[Dict[str, Any]]
    total_amount: float
    confirmation_number: str
    tracking_number: Optional[str] = None
    receipt_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
