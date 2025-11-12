"""
Generation model for Creator platform
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, Float, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime

from apps.shared.models.base import BaseModel


class GenerationStatus(str, Enum):
    """Generation job status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Generation(BaseModel):
    """
    A single generation job and its outputs.

    Tracks the execution of a workflow and stores results.
    """

    __tablename__ = "generations"

    # Ownership
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Job details
    name = Column(String(255), nullable=True)
    """User-provided name for this generation"""

    status = Column(
        SQLEnum(GenerationStatus),
        default=GenerationStatus.QUEUED,
        nullable=False,
        index=True
    )

    # ComfyUI integration
    comfyui_prompt_id = Column(String(255), nullable=True, unique=True, index=True)
    """The prompt ID returned by ComfyUI"""

    # Input parameters
    input_parameters = Column(JSONB, default=dict, nullable=False)
    """
    The parameters used for this generation:
    {
        "prompt": "beautiful sunset",
        "negative_prompt": "low quality",
        "steps": 30,
        "cfg": 7.5,
        "seed": 12345
    }
    """

    workflow_snapshot = Column(JSONB, nullable=True)
    """Snapshot of the workflow JSON at generation time"""

    # Output
    output_urls = Column(JSONB, default=list, nullable=False)
    """
    URLs of generated images:
    [
        "https://storage.example.com/user123/gen456_0.png",
        "https://storage.example.com/user123/gen456_1.png"
    ]
    """

    output_count = Column(Integer, default=0, nullable=False)
    thumbnail_url = Column(String(500), nullable=True)

    # Timing
    queued_at = Column("queued_at", nullable=True)
    started_at = Column("started_at", nullable=True)
    completed_at = Column("completed_at", nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Progress tracking
    progress_percent = Column(Integer, default=0, nullable=False)
    progress_message = Column(String(255), nullable=True)

    # User interaction
    is_favorited = Column(Boolean, default=False, nullable=False, index=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    notes = Column(Text, nullable=True)

    # Additional data
    tags = Column(JSONB, default=list, nullable=False)
    custom_metadata = Column(JSONB, default=dict, nullable=False)
    """
    Additional generation metadata:
    {
        "model": "sd_v1_5",
        "scheduler": "karras",
        "dimensions": "1920x1080",
        "file_size_mb": 4.2
    }
    """

    # Credits/cost
    credits_used = Column(Integer, default=1, nullable=False)

    # Webhook
    webhook_sent = Column(Boolean, default=False, nullable=False)
    webhook_sent_at = Column("webhook_sent_at", nullable=True)

    # Relationships
    user = relationship("User", back_populates="generations")
    project = relationship("Project", back_populates="generations")
    workflow = relationship("Workflow", back_populates="generations")

    def __repr__(self) -> str:
        return f"<Generation(id={self.id}, status={self.status}, user_id={self.user_id})>"

    def mark_processing(self):
        """Mark generation as processing"""
        self.status = GenerationStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.progress_percent = 1

    def mark_completed(self, output_urls: list[str], duration: float = None):
        """Mark generation as completed"""
        self.status = GenerationStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.output_urls = output_urls
        self.output_count = len(output_urls)
        self.progress_percent = 100

        if duration:
            self.duration_seconds = duration
        elif self.started_at:
            delta = datetime.utcnow() - self.started_at
            self.duration_seconds = delta.total_seconds()

        # Set thumbnail to first output
        if output_urls:
            self.thumbnail_url = output_urls[0]

    def mark_failed(self, error: str, details: dict = None):
        """Mark generation as failed"""
        self.status = GenerationStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error
        self.error_details = details or {}

        if self.started_at:
            delta = datetime.utcnow() - self.started_at
            self.duration_seconds = delta.total_seconds()

    def mark_cancelled(self):
        """Mark generation as cancelled"""
        self.status = GenerationStatus.CANCELLED
        self.completed_at = datetime.utcnow()

        if self.started_at:
            delta = datetime.utcnow() - self.started_at
            self.duration_seconds = delta.total_seconds()

    def update_progress(self, percent: int, message: str = None):
        """Update generation progress"""
        self.progress_percent = max(0, min(100, percent))
        if message:
            self.progress_message = message

    @property
    def is_terminal(self) -> bool:
        """Check if generation is in a terminal state"""
        return self.status in [
            GenerationStatus.COMPLETED,
            GenerationStatus.FAILED,
            GenerationStatus.CANCELLED
        ]
