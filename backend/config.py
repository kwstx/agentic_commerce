from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

class Settings(BaseSettings):
    # API Keys (Protected via SecretStr to prevent accidental logging)
    STRIPE_SECRET_KEY: SecretStr = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: SecretStr = Field(..., env="STRIPE_WEBHOOK_SECRET")
    ADYEN_API_KEY: SecretStr = Field(..., env="ADYEN_API_KEY")
    SHOPIFY_ACCESS_TOKEN: SecretStr = Field("mock_token", env="SHOPIFY_ACCESS_TOKEN")
    
    # Database
    DATABASE_URL: str = Field("postgresql://user:pass@localhost/dbname", env="DATABASE_URL")
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Security
    JWT_SECRET_KEY: SecretStr = Field(..., env="JWT_SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OTEL
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field("http://localhost:4317", env="OTEL_EXPORTER_OTLP_ENDPOINT")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
