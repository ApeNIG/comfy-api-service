"""Production environment configuration"""

from .base import Settings


class ProductionSettings(Settings):
    """Production-specific settings"""

    # Strict production settings
    DEBUG: bool = False
    DATABASE_ECHO: bool = False

    # Higher connection pools for production load
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    REDIS_MAX_CONNECTIONS: int = 100

    # Strict CORS (set actual domains)
    CORS_ORIGINS: list = [
        "https://app.yourproductdomain.com",
        "https://www.yourproductdomain.com",
    ]

    # Production rate limits
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # JSON logging for production (easier to parse)
    LOG_FORMAT: str = "json"
    LOG_LEVEL: str = "INFO"

    # Enable monitoring in production
    METRICS_ENABLED: bool = True
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of requests

    # Higher worker concurrency
    WORKER_CONCURRENCY: int = 20

    # Use HTTPS for MinIO in production
    MINIO_SECURE: bool = True

    class Config:
        env_file = ".env.production"
        env_file_encoding = "utf-8"
        case_sensitive = True
