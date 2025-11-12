"""
Project model for Creator platform
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from apps.shared.models.base import BaseModel


class Project(BaseModel):
    """
    Project contains workflows and generations.

    A project represents a collection of related workflows and their outputs.
    Example: "Marketing Campaign 2024", "Product Photoshoot", "Brand Assets"
    """

    __tablename__ = "projects"

    # Ownership
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Project details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Organization
    folder = Column(String(255), nullable=True)  # For organizing projects
    tags = Column(JSONB, default=list, nullable=False)  # ["marketing", "portrait"]
    color = Column(String(7), default="#FF6E6B", nullable=False)  # Hex color for UI

    # Settings
    is_archived = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # For sharing
    public_slug = Column(String(255), nullable=True, unique=True, index=True)

    # Custom metadata
    custom_metadata = Column(JSONB, default=dict, nullable=False)
    """
    Flexible metadata field for custom project data:
    {
        "client": "Acme Corp",
        "deadline": "2024-12-31",
        "budget": 5000,
        "custom_field": "value"
    }
    """

    # Stats (denormalized for performance)
    workflow_count = Column(Integer, default=0, nullable=False)
    generation_count = Column(Integer, default=0, nullable=False)
    last_generation_at = Column(
        "last_generation_at",
        nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="projects")
    workflows = relationship(
        "Workflow",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Workflow.created_at.desc()"
    )
    generations = relationship(
        "Generation",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Generation.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, user_id={self.user_id})>"

    def increment_workflow_count(self):
        """Increment workflow counter"""
        self.workflow_count += 1

    def increment_generation_count(self):
        """Increment generation counter"""
        from datetime import datetime
        self.generation_count += 1
        self.last_generation_at = datetime.utcnow()
