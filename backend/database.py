import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from cryptography.fernet import Fernet

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/agentic_commerce")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode())

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Null for OAuth users
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
    payment_tokens = relationship("PaymentTokenVault", back_populates="user")
    spending_limits = relationship("SpendingLimit", back_populates="user", uselist=False)

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String, nullable=False)  # google, github, etc.
    provider_user_id = Column(String, nullable=False)
    user = relationship("User", back_populates="oauth_accounts")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    encrypted_data = Column(Text, nullable=False)  # Encrypted JSON blob
    user = relationship("User", back_populates="preferences")

    def set_preferences(self, data: dict):
        import json
        json_data = json.dumps(data)
        self.encrypted_data = fernet.encrypt(json_data.encode()).decode()

    def get_preferences(self) -> dict:
        import json
        decrypted = fernet.decrypt(self.encrypted_data.encode()).decode()
        return json.loads(decrypted)

class PaymentTokenVault(Base):
    __tablename__ = "payment_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String, nullable=False)  # e.g., "stripe"
    token_reference = Column(String, nullable=False)  # Tokenized reference
    last_four = Column(String(4))
    card_type = Column(String)
    user = relationship("User", back_populates="payment_tokens")

class SpendingLimit(Base):
    __tablename__ = "spending_limits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    per_transaction_limit = Column(Float, default=100.0)
    daily_limit = Column(Float, default=500.0)
    daily_spent = Column(Float, default=0.0)
    user = relationship("User", back_populates="spending_limits")

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_details = Column(JSON, nullable=False)
    reasoning = Column(Text)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_name = Column(String)
    merchant = Column(String)
    price = Column(Float)
    status = Column(String)  # pending, completed, failed
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_id = Column(String, index=True) # Linked to a session/workflow
    step = Column(String) # e.g., "inventory_check", "payment_processing"
    action = Column(String) # e.g., "EXECUTE", "ROLLBACK"
    decision = Column(Text) # LLM reasoning or rule-based decision
    api_response_summary = Column(JSON) # Truncated/Summarized API response
    status = Column(String) # success, failure
    timestamp = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_id = Column(String, unique=True)
    merchant = Column(String)
    items = Column(JSON)
    total_amount = Column(Float)
    confirmation_number = Column(String)
    tracking_number = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)
    status = Column(String) # placed, shipped, delivered, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

# Engine & Session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
