"""Development environment configuration"""

from .base import Settings


class DevelopmentSettings(Settings):
    """Development-specific settings"""

    # Enable debug mode
    DEBUG: bool = True
    DATABASE_ECHO: bool = True  # Log SQL queries

    # Relaxed CORS for local development
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:8000",
    ]

    # Lower rate limits for testing
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_PER_HOUR: int = 5000

    # Console logging for development
    LOG_FORMAT: str = "console"
    LOG_LEVEL: str = "DEBUG"

    # Disable some features in development
    SENTRY_DSN: str | None = None  # No error tracking locally
    METRICS_ENABLED: bool = False  # No metrics locally

    # Email goes to console in development
    SMTP_HOST: str | None = None  # Will log emails instead

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
