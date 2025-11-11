"""Testing environment configuration"""

from .base import Settings


class TestingSettings(Settings):
    """Test-specific settings"""

    # Test database (separate from development)
    DATABASE_URL: str = "postgresql://test:test@localhost:5432/comfyui_test"
    DATABASE_ECHO: bool = False  # Don't spam test output

    # Test Redis
    REDIS_URL: str = "redis://localhost:6379/1"  # Different DB number

    # Disable external services in tests
    SENTRY_DSN: str | None = None
    METRICS_ENABLED: bool = False
    SMTP_HOST: str | None = None

    # Mock ComfyUI in tests
    COMFYUI_URL: str = "http://mock-comfyui:8188"

    # Disable rate limiting in tests
    RATE_LIMIT_ENABLED: bool = False

    # Fast password hashing for tests
    PASSWORD_HASH_ROUNDS: int = 4  # Minimum for bcrypt

    # Short JWT expiration for testing
    JWT_EXPIRATION_HOURS: int = 1

    # Console logging in tests
    LOG_FORMAT: str = "console"
    LOG_LEVEL: str = "WARNING"  # Reduce test noise

    # Disable all optional features
    FEATURE_DRIVE_INTEGRATION: bool = False
    FEATURE_STRIPE_BILLING: bool = False
    FEATURE_EMAIL_NOTIFICATIONS: bool = False

    class Config:
        env_file = ".env.test"
        env_file_encoding = "utf-8"
        case_sensitive = True
