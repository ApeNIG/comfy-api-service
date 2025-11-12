"""
Base configuration settings using Pydantic Settings.
All environment-specific configs inherit from this.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import Field


class Settings(BaseSettings):
    """Base settings for all environments"""

    # ============================================================================
    # Application Settings
    # ============================================================================
    APP_NAME: str = "ComfyUI Platform"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = False
    API_VERSION: str = "v1"
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")

    # ============================================================================
    # Database Settings (Postgres / Supabase)
    # ============================================================================
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600  # 1 hour
    DATABASE_ECHO: bool = False  # Log SQL queries

    # Supabase Settings (optional - if using Supabase)
    SUPABASE_URL: Optional[str] = Field(default=None, env="SUPABASE_URL")
    SUPABASE_ANON_KEY: Optional[str] = Field(default=None, env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_KEY")

    # ============================================================================
    # Redis Settings
    # ============================================================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_DECODE_RESPONSES: bool = True

    # ============================================================================
    # Storage Settings (MinIO / S3)
    # ============================================================================
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", env="MINIO_SECRET_KEY")
    MINIO_SECURE: bool = False  # Use HTTPS
    MINIO_REGION: str = "us-east-1"

    # Storage buckets
    MINIO_BUCKET_NAME: str = Field(default="comfyui-artifacts", env="MINIO_BUCKET_NAME")
    STORAGE_UPLOADS_BUCKET: str = "uploads"
    STORAGE_OUTPUTS_BUCKET: str = "outputs"

    # ============================================================================
    # ComfyUI Settings
    # ============================================================================
    COMFYUI_URL: str = Field(..., env="COMFYUI_URL")
    COMFYUI_TIMEOUT: float = 120.0
    COMFYUI_MAX_RETRIES: int = 3
    COMFYUI_RETRY_DELAY: float = 2.0

    # ============================================================================
    # Google OAuth Settings
    # ============================================================================
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(..., env="GOOGLE_REDIRECT_URI")

    # Google Drive API scopes
    GOOGLE_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    # ============================================================================
    # Stripe Settings
    # ============================================================================
    STRIPE_PUBLIC_KEY: str = Field(..., env="STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY: str = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(..., env="STRIPE_WEBHOOK_SECRET")

    # Stripe product IDs (set after creating in Stripe dashboard)
    STRIPE_FREE_PRICE_ID: Optional[str] = None
    STRIPE_CREATOR_PRICE_ID: Optional[str] = None
    STRIPE_STUDIO_PRICE_ID: Optional[str] = None

    # ============================================================================
    # Security Settings
    # ============================================================================
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # For JWT signing
    ENCRYPTION_KEY: str = Field(..., env="ENCRYPTION_KEY")  # For token encryption

    # JWT settings
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 168  # 7 days

    # Password hashing
    PASSWORD_HASH_ALGORITHM: str = "bcrypt"
    PASSWORD_HASH_ROUNDS: int = 12

    # ============================================================================
    # API Rate Limiting
    # ============================================================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Creator tier rate limits
    CREATOR_FREE_MONTHLY_LIMIT: int = 10
    CREATOR_PAID_MONTHLY_LIMIT: int = 100
    CREATOR_STUDIO_MONTHLY_LIMIT: int = 500

    # ============================================================================
    # Email Settings (SMTP)
    # ============================================================================
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = "noreply@comfyui-platform.com"
    SMTP_FROM_NAME: str = "ComfyUI Platform"

    # ============================================================================
    # CORS Settings
    # ============================================================================
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ============================================================================
    # Observability Settings
    # ============================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "console"

    # Sentry (error tracking)
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Prometheus metrics
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    # ============================================================================
    # Feature Flags
    # ============================================================================
    FEATURE_DRIVE_INTEGRATION: bool = True
    FEATURE_STRIPE_BILLING: bool = True
    FEATURE_EMAIL_NOTIFICATIONS: bool = True
    FEATURE_USAGE_TRACKING: bool = True

    # ============================================================================
    # Worker Settings
    # ============================================================================
    WORKER_CONCURRENCY: int = 10
    WORKER_MAX_RETRIES: int = 3
    WORKER_RETRY_DELAY: float = 5.0

    # Drive polling interval (minutes)
    DRIVE_POLL_INTERVAL_MINUTES: int = 5

    # ============================================================================
    # File Upload Limits
    # ============================================================================
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/quicktime"]

    # ============================================================================
    # Pydantic Config
    # ============================================================================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Export settings instance
settings = Settings()
