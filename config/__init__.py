"""
Configuration management

Usage:
    from config import settings

    # Settings automatically loaded based on ENVIRONMENT variable
    print(settings.DATABASE_URL)
    print(settings.DEBUG)
"""

import os
from .base import Settings
from .development import DevelopmentSettings
from .production import ProductionSettings
from .testing import TestingSettings

# Determine environment from env variable
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Map environments to setting classes
SETTINGS_MAP = {
    "development": DevelopmentSettings,
    "dev": DevelopmentSettings,  # Alias for development
    "production": ProductionSettings,
    "prod": ProductionSettings,  # Alias for production
    "testing": TestingSettings,
    "test": TestingSettings,  # Alias for testing
}

# Get the appropriate settings class
SettingsClass = SETTINGS_MAP.get(ENVIRONMENT, DevelopmentSettings)

# Create settings instance
settings: Settings = SettingsClass()

# Export for convenience
__all__ = ["settings", "Settings"]
