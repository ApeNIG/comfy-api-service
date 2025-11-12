"""
Workflow model for Creator platform
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from enum import Enum

from apps.shared.models.base import BaseModel


class WorkflowCategory(str, Enum):
    """Workflow categories for organization"""
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    INPAINTING = "inpainting"
    UPSCALING = "upscaling"
    CUSTOM = "custom"


class WorkflowVisibility(str, Enum):
    """Workflow sharing visibility"""
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"  # Public but not discoverable


class Workflow(BaseModel):
    """
    ComfyUI workflow definition.

    Stores the JSON workflow, parameters, and version history.
    """

    __tablename__ = "workflows"

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

    # Workflow details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        SQLEnum(WorkflowCategory),
        default=WorkflowCategory.TEXT_TO_IMAGE,
        nullable=False,
        index=True
    )

    # ComfyUI workflow JSON
    workflow_json = Column(JSONB, nullable=False)
    """
    The complete ComfyUI workflow in API format:
    {
        "3": {"inputs": {...}, "class_type": "KSampler"},
        "4": {"inputs": {...}, "class_type": "CheckpointLoader"},
        ...
    }
    """

    # Workflow metadata
    thumbnail_url = Column(String(500), nullable=True)
    preview_image_url = Column(String(500), nullable=True)
    tags = Column(JSONB, default=list, nullable=False)

    # Parameters (for UI form generation)
    parameters = Column(JSONB, default=dict, nullable=False)
    """
    Exposed parameters for easy customization:
    {
        "prompt": {
            "type": "text",
            "label": "Prompt",
            "default": "beautiful landscape",
            "node_id": "6",
            "node_input": "text"
        },
        "steps": {
            "type": "number",
            "label": "Sampling Steps",
            "default": 25,
            "min": 10,
            "max": 50,
            "node_id": "3",
            "node_input": "steps"
        }
    }
    """

    # Version control
    version = Column(Integer, default=1, nullable=False)
    parent_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True
    )
    version_notes = Column(Text, nullable=True)

    # Sharing
    visibility = Column(
        SQLEnum(WorkflowVisibility),
        default=WorkflowVisibility.PRIVATE,
        nullable=False,
        index=True
    )
    public_slug = Column(String(255), nullable=True, unique=True, index=True)
    is_template = Column(Boolean, default=False, nullable=False, index=True)
    """Official templates can be copied by any user"""

    # Usage stats
    use_count = Column(Integer, default=0, nullable=False)
    copy_count = Column(Integer, default=0, nullable=False)
    """How many times this workflow has been copied by others"""

    # Feature flags
    features = Column(JSONB, default=dict, nullable=False)
    """
    Feature toggles for workflow components:
    {
        "use_adetailer": true,
        "use_upscaling": false,
        "use_gemini": false,
        "output_format": "png"
    }
    """

    # Estimated costs/credits
    estimated_credits = Column(Integer, default=1, nullable=False)
    """How many credits this workflow costs to run"""

    # Relationships
    user = relationship("User", back_populates="workflows")
    project = relationship("Project", back_populates="workflows")
    generations = relationship(
        "Generation",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    versions = relationship(
        "Workflow",
        backref="parent_version",
        remote_side="Workflow.id"
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, version={self.version})>"

    def increment_use_count(self):
        """Increment usage counter"""
        self.use_count += 1

    def increment_copy_count(self):
        """Increment copy counter"""
        self.copy_count += 1

    def create_version(self, workflow_json: dict, notes: str = None):
        """Create a new version of this workflow"""
        new_version = Workflow(
            user_id=self.user_id,
            project_id=self.project_id,
            name=self.name,
            description=self.description,
            category=self.category,
            workflow_json=workflow_json,
            parameters=self.parameters.copy(),
            tags=self.tags.copy(),
            version=self.version + 1,
            parent_version_id=self.id,
            version_notes=notes,
            visibility=self.visibility,
            features=self.features.copy(),
            estimated_credits=self.estimated_credits
        )
        return new_version
