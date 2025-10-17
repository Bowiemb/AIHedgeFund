"""Application configuration."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://aihedge:aihedge123@localhost:5432/aihedge"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # S3 Storage
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "aihedge-filings"
    S3_REGION: str = "us-east-1"

    # SEC EDGAR
    SEC_CONTACT_EMAIL: str = "contact@aihedgefund.com"
    SEC_USER_AGENT: str = "AIHedgeFund/1.0"
    SEC_RATE_LIMIT: int = 10  # requests per second
    SEC_CACHE_TTL: int = 86400  # 24 hours

    # Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 1
    REFRESH_TOKEN_EXPIRY_DAYS: int = 7
    API_KEY_PREFIX: str = "aihf_live_"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLIC_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Rate Limiting
    RATE_LIMIT_FREE: int = 100
    RATE_LIMIT_PRO: int = 10000
    RATE_LIMIT_ENTERPRISE: int = 1000000
    ROW_LIMIT_FREE: int = 100
    ROW_LIMIT_PRO: int = 1000
    ROW_LIMIT_ENTERPRISE: int = 100000

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Monitoring
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "aihedgefund-api"


settings = Settings()
