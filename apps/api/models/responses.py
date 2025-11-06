"""Response models for API endpoints."""

from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageMetadata(BaseModel):
    """Metadata about the generated image."""

    prompt: str = Field(..., description="The prompt used to generate the image")
    negative_prompt: Optional[str] = Field(None, description="The negative prompt used")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    steps: int = Field(..., description="Number of sampling steps")
    cfg_scale: float = Field(..., description="CFG scale value")
    sampler: str = Field(..., description="Sampler used")
    seed: int = Field(..., description="Seed used for generation")
    model: str = Field(..., description="Model checkpoint used")
    generation_time: Optional[float] = Field(None, description="Time taken to generate (seconds)")


class ImageResponse(BaseModel):
    """Response model for image generation."""

    job_id: str = Field(..., description="Unique identifier for this generation job")

    status: JobStatus = Field(..., description="Current status of the job")

    image_url: Optional[str] = Field(
        None,
        description="URL to download the generated image (available when status=completed)"
    )

    image_data: Optional[str] = Field(
        None,
        description="Base64-encoded image data (if requested)"
    )

    error: Optional[str] = Field(
        None,
        description="Error message if status=failed"
    )

    metadata: Optional[ImageMetadata] = Field(
        None,
        description="Metadata about the generation"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the job was created"
    )

    started_at: Optional[datetime] = Field(
        None,
        description="When the job started processing"
    )

    completed_at: Optional[datetime] = Field(
        None,
        description="When the job completed"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "abc123-def456-ghi789",
                    "status": "completed",
                    "image_url": "/api/v1/images/abc123-def456-ghi789.png",
                    "metadata": {
                        "prompt": "A beautiful landscape",
                        "width": 1024,
                        "height": 1024,
                        "steps": 30,
                        "cfg_scale": 7.5,
                        "sampler": "euler_a",
                        "seed": 42,
                        "model": "sd_xl_base_1.0.safetensors",
                        "generation_time": 15.3
                    },
                    "created_at": "2025-11-06T12:00:00Z",
                    "started_at": "2025-11-06T12:00:01Z",
                    "completed_at": "2025-11-06T12:00:16Z"
                }
            ]
        }
    }


class BatchImageResponse(BaseModel):
    """Response model for batch image generation."""

    batch_id: str = Field(..., description="Unique identifier for this batch")
    jobs: list[ImageResponse] = Field(..., description="Individual job responses")
    total: int = Field(..., description="Total number of jobs in batch")
    completed: int = Field(0, description="Number of completed jobs")
    failed: int = Field(0, description="Number of failed jobs")


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""

    error: ErrorDetail = Field(..., description="Error details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Width must be divisible by 8",
                        "details": {
                            "field": "width",
                            "provided_value": 513
                        },
                        "request_id": "abc-123-def-456",
                        "timestamp": "2025-11-06T12:00:00Z"
                    }
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall service status")
    api_version: str = Field(..., description="API version")
    comfyui_status: str = Field(..., description="ComfyUI service status")
    comfyui_url: str = Field(..., description="ComfyUI URL")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "api_version": "1.0.0",
                    "comfyui_status": "connected",
                    "comfyui_url": "http://localhost:8188",
                    "timestamp": "2025-11-06T12:00:00Z"
                }
            ]
        }
    }


class ModelInfo(BaseModel):
    """Information about an available model."""

    name: str = Field(..., description="Model filename")
    path: str = Field(..., description="Path to model file")
    size: Optional[int] = Field(None, description="File size in bytes")
    type: str = Field(..., description="Model type (checkpoint, lora, etc.)")


class ModelsListResponse(BaseModel):
    """Response with list of available models."""

    models: list[ModelInfo] = Field(..., description="Available models")
    total: int = Field(..., description="Total number of models")
