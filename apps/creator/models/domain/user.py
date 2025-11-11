"""
User domain model

Represents a creator user with OAuth credentials and Drive integration.
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship

from apps.shared.models.base import BaseModel
from apps.shared.models.enums import UserRole


class User(BaseModel):
    """
    Creator user with Google OAuth and Drive integration.

    Relationships:
        - subscriptions: One-to-many with Subscription
        - jobs: One-to-many with Job
    """

    __tablename__ = "users"

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Optional for OAuth-only users
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default=UserRole.USER.value, nullable=False)

    # Google OAuth
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    google_access_token = Column(String(500), nullable=True)  # Encrypted
    google_refresh_token = Column(String(500), nullable=True)  # Encrypted
    google_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Google Drive Integration
    drive_folder_id = Column(String(255), nullable=True)  # Folder we watch for new files
    drive_output_folder_id = Column(String(255), nullable=True)  # Where we put results
    drive_webhook_id = Column(String(255), nullable=True)  # Drive push notification channel
    drive_webhook_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Usage Tracking
    total_jobs_run = Column(Integer, default=0, nullable=False)
    total_credits_used = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps (inherited from BaseModel)
    # id, created_at, updated_at

    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", lazy="dynamic")
    jobs = relationship("Job", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

    @property
    def has_active_subscription(self) -> bool:
        """Check if user has an active subscription."""
        from apps.shared.models.enums import SubscriptionStatus

        return self.subscriptions.filter_by(
            status=SubscriptionStatus.ACTIVE.value
        ).first() is not None

    @property
    def has_drive_connected(self) -> bool:
        """Check if user has connected Google Drive."""
        return self.google_access_token is not None and self.drive_folder_id is not None

    @property
    def needs_token_refresh(self) -> bool:
        """Check if Google token needs refreshing."""
        if not self.google_token_expires_at:
            return False

        # Refresh if expiring within 5 minutes
        from datetime import timedelta
        return datetime.utcnow() + timedelta(minutes=5) >= self.google_token_expires_at
