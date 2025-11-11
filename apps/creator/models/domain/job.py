"""
Job domain model

Represents a single image processing job from Drive upload to completion.
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from apps.shared.models.base import BaseModel
from apps.shared.models.enums import JobStatus


class Job(BaseModel):
    """
    Image processing job from Drive upload to completion.

    Lifecycle:
        1. User uploads file to Drive folder
        2. Job created with status=QUEUED
        3. Worker picks up job, status=PROCESSING
        4. ComfyUI processes image
        5. Result uploaded to Drive output folder
        6. Job status=COMPLETED

    Relationships:
        - user: Many-to-one with User
    """

    __tablename__ = "jobs"

    # Foreign Keys
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job Status
    status = Column(
        String(50),
        default=JobStatus.QUEUED.value,
        nullable=False,
        index=True,
    )

    # Input File (from Google Drive)
    input_file_id = Column(String(255), nullable=False, index=True)  # Drive file ID
    input_file_name = Column(String(500), nullable=False)
    input_file_url = Column(String(1000), nullable=True)  # Drive download URL
    input_file_size = Column(Integer, nullable=True)  # Bytes

    # Processing Configuration
    preset_name = Column(String(100), nullable=False, index=True)  # e.g., "thumbnail"
    workflow_id = Column(String(100), nullable=False)  # ComfyUI workflow ID
    workflow_params = Column(JSON, nullable=True)  # Custom parameters for workflow

    # Output File (uploaded back to Drive)
    output_file_id = Column(String(255), nullable=True, index=True)  # Drive file ID
    output_file_name = Column(String(500), nullable=True)
    output_file_url = Column(String(1000), nullable=True)  # Drive file URL
    output_file_size = Column(Integer, nullable=True)  # Bytes

    # ComfyUI Processing
    comfyui_prompt_id = Column(String(255), nullable=True, index=True)  # ComfyUI job ID
    comfyui_node_errors = Column(JSON, nullable=True)  # Errors from ComfyUI nodes
    comfyui_execution_time = Column(Integer, nullable=True)  # Seconds

    # Timing
    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    # Error Handling
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)  # e.g., "ComfyUIError", "DriveError"
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Metrics
    credits_consumed = Column(Integer, default=1, nullable=False)

    # Timestamps (inherited from BaseModel)
    # id, created_at, updated_at

    # Relationships
    user = relationship("User", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, status={self.status}, preset={self.preset_name})>"

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state (won't change)."""
        return self.status in [
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        ]

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED.value
            and self.retry_count < self.max_retries
        )

    @property
    def processing_duration(self) -> int | None:
        """Get total processing time in seconds."""
        if not self.started_at or not self.completed_at:
            return None

        delta = self.completed_at - self.started_at
        return int(delta.total_seconds())

    @property
    def queue_wait_time(self) -> int | None:
        """Get time spent waiting in queue (seconds)."""
        if not self.queued_at or not self.started_at:
            return None

        delta = self.started_at - self.queued_at
        return int(delta.total_seconds())

    def mark_queued(self) -> None:
        """Mark job as queued."""
        self.status = JobStatus.QUEUED.value
        self.queued_at = datetime.utcnow()

    def mark_processing(self, comfyui_prompt_id: str | None = None) -> None:
        """Mark job as processing."""
        self.status = JobStatus.PROCESSING.value
        self.started_at = datetime.utcnow()
        if comfyui_prompt_id:
            self.comfyui_prompt_id = comfyui_prompt_id

    def mark_completed(
        self,
        output_file_id: str,
        output_file_name: str,
        output_file_url: str | None = None,
    ) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        self.output_file_id = output_file_id
        self.output_file_name = output_file_name
        self.output_file_url = output_file_url

    def mark_failed(self, error_message: str, error_type: str | None = None) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED.value
        self.failed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_type = error_type

    def mark_cancelled(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED.value
        self.completed_at = datetime.utcnow()

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1
