"""
Configuration settings for the ComfyUI API Service.

Uses pydantic-settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_prefix: str = "cui"

    # ARQ (Job Queue) Configuration
    arq_queue_name: str = "default"
    arq_max_jobs: int = 1000
    arq_worker_concurrency: int = 5

    # Job Settings
    job_timeout: int = 1200  # 20 minutes max per job
    max_batch_size: int = 10  # Max images per batch
    max_megapixels: int = 4  # 2048x2048 ~ 4.2MP

    # Storage Configuration (MinIO/S3)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "comfyui-artifacts"
    minio_secure: bool = False  # Use HTTPS
    artifact_url_ttl: int = 3600  # 1 hour for presigned URLs

    # ComfyUI Configuration
    comfyui_url: str = "http://localhost:8188"
    comfyui_timeout: float = 300.0

    # Feature Flags
    jobs_enabled: bool = True  # Enable async job queue
    websocket_enabled: bool = True  # Enable WebSocket progress updates

    # API Configuration
    api_version: str = "1.0.1"
    service_name: str = "ComfyUI API Service"
    max_upload_size: int = 10_485_760  # 10MB

    # Development
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
