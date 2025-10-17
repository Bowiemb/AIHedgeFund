"""Worker configuration."""

from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Worker settings."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://aihedge:aihedge123@localhost:5432/aihedge"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # S3
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "aihedge-filings"
    S3_REGION: str = "us-east-1"

    # SEC EDGAR
    SEC_CONTACT_EMAIL: str = "contact@aihedgefund.com"
    SEC_USER_AGENT: str = "AIHedgeFund/1.0"

    # Worker settings
    WORKER_CONCURRENCY: int = 4
    INGESTION_BATCH_SIZE: int = 100

    class Config:
        env_file = ".env"


settings = WorkerSettings()
