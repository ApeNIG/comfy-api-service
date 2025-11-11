"""
Base SQLAlchemy model with common fields

All domain models should inherit from this.
"""

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from apps.shared.infrastructure.database import Base


class BaseModel(Base):
    """
    Abstract base model with common fields.

    All models inherit:
    - id (UUID primary key)
    - created_at (timestamp)
    - updated_at (auto-updating timestamp)

    Usage:
        class User(BaseModel):
            __tablename__ = "users"

            email = Column(String, unique=True)
            name = Column(String)
    """

    __abstract__ = True  # Don't create table for this class

    # UUID primary key (more secure than auto-increment)
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self) -> dict:
        """
        Convert model to dictionary.

        Returns:
            Dictionary with all non-private attributes
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}(id={self.id})>"
