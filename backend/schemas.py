from pydantic import BaseModel
from typing import List, Optional

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

class UserProfileSchema(BaseModel):
    username: str
    preferences: List[str]

class TransactionSchema(BaseModel):
    product_name: str
    merchant: str
    price: float
    status: str
