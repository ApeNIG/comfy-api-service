"""
Job models and schemas for async job processing.

Defines request/response models for job submission, status checking,
and result retrieval.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job lifecycle states."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"


class JobArtifact(BaseModel):
    """Generated artifact (image) with metadata."""
    url: str = Field(..., description="Presigned URL to download artifact")
    seed: Optional[int] = Field(None, description="Seed used for generation")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    meta: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class JobResult(BaseModel):
    """Job result containing generated artifacts."""
    artifacts: list[JobArtifact] = Field(
        default_factory=list,
        description="List of generated images"
    )
    generation_time: Optional[float] = Field(
        None,
        description="Time taken to generate (seconds)"
    )


class JobTimestamps(BaseModel):
    """Job lifecycle timestamps."""
    queued_at: datetime = Field(..., description="When job was queued")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    finished_at: Optional[datetime] = Field(None, description="When job completed")


class JobError(BaseModel):
    """Error information for failed jobs."""
    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type/class")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")


class JobResponse(BaseModel):
    """
    Complete job status response.

    Returned by GET /api/v1/jobs/{id}
    """
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Progress from 0.0 (started) to 1.0 (completed)"
    )
    submitted_by: Optional[str] = Field(
        None,
        description="Token/user identifier (only visible to owner)"
    )
    params: Optional[dict[str, Any]] = Field(
        None,
        description="Job parameters (only visible to owner)"
    )
    result: Optional[JobResult] = Field(
        None,
        description="Job result (available when status=succeeded)"
    )
    error: Optional[JobError] = Field(
        None,
        description="Error details (available when status=failed)"
    )
    timestamps: JobTimestamps = Field(..., description="Job lifecycle timestamps")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "j_a1b2c3d4e5f6",
                "status": "succeeded",
                "progress": 1.0,
                "submitted_by": "tok_xyz123",
                "params": {
                    "prompt": "A beautiful sunset over mountains",
                    "width": 1024,
                    "height": 1024,
                    "steps": 30
                },
                "result": {
                    "artifacts": [
                        {
                            "url": "https://storage.example.com/jobs/j_abc123/image_0.png?signature=...",
                            "seed": 42,
                            "width": 1024,
                            "height": 1024
                        }
                    ],
                    "generation_time": 15.3
                },
                "error": None,
                "timestamps": {
                    "queued_at": "2025-11-06T12:00:00Z",
                    "started_at": "2025-11-06T12:00:02Z",
                    "finished_at": "2025-11-06T12:00:17Z"
                }
            }
        }


class JobCreateResponse(BaseModel):
    """
    Response when creating a new job.

    Returned by POST /api/v1/jobs
    """
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Initial status (always 'queued')")
    queued_at: datetime = Field(..., description="Timestamp when job was queued")
    location: str = Field(..., description="URL to check job status")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "j_a1b2c3d4e5f6",
                "status": "queued",
                "queued_at": "2025-11-06T12:00:00Z",
                "location": "/api/v1/jobs/j_a1b2c3d4e5f6"
            }
        }


class JobCancelResponse(BaseModel):
    """Response when cancelling a job."""
    job_id: str = Field(..., description="Job identifier")
    message: str = Field(..., description="Cancellation status message")
    status: JobStatus = Field(..., description="Current job status after cancellation request")


class JobListResponse(BaseModel):
    """
    Response when listing jobs.

    Returned by GET /api/v1/jobs
    """
    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")

    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "job_id": "j_a1b2c3d4e5f6",
                        "status": "succeeded",
                        "progress": 1.0,
                        "timestamps": {
                            "queued_at": "2025-11-06T12:00:00Z",
                            "started_at": "2025-11-06T12:00:02Z",
                            "finished_at": "2025-11-06T12:00:17Z"
                        }
                    }
                ],
                "total": 1,
                "limit": 20,
                "offset": 0
            }
        }


class WebSocketProgressMessage(BaseModel):
    """
    WebSocket progress update message.

    Sent via WS /ws/jobs/{id}
    """
    type: str = Field(..., description="Message type (status, progress, log, artifact, done)")
    status: Optional[JobStatus] = Field(None, description="Job status (for type=status or type=done)")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Progress 0-1 (for type=progress)")
    message: Optional[str] = Field(None, description="Log message (for type=log or type=progress)")
    url: Optional[str] = Field(None, description="Artifact URL (for type=artifact)")
    result: Optional[JobResult] = Field(None, description="Complete result (for type=done)")
    error: Optional[JobError] = Field(None, description="Error details (for type=done with status=failed)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "status",
                    "status": "running",
                    "progress": 0.0
                },
                {
                    "type": "progress",
                    "progress": 0.42,
                    "message": "Denoising step 12/28"
                },
                {
                    "type": "log",
                    "message": "Uploading artifacts to storage"
                },
                {
                    "type": "artifact",
                    "url": "https://storage.example.com/jobs/j_abc123/image_0.png"
                },
                {
                    "type": "done",
                    "status": "succeeded",
                    "result": {
                        "artifacts": [
                            {
                                "url": "https://storage.example.com/jobs/j_abc123/image_0.png",
                                "seed": 42
                            }
                        ]
                    }
                }
            ]
        }
