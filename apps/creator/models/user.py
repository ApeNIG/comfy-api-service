"""
User model for Creator platform
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from apps.shared.models.base import BaseModel
from apps.shared.models.enums import UserRole, SubscriptionTier, SubscriptionStatus


class User(BaseModel):
    """
    User account in Creator platform.

    Handles authentication, subscription, and usage tracking.
    """

    __tablename__ = "users"

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Profile
    full_name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Subscription
    subscription_tier = Column(
        SQLEnum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    subscription_status = Column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    monthly_generation_count = Column(Integer, default=0, nullable=False)
    monthly_generation_reset_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    total_generations = Column(Integer, default=0, nullable=False)

    # API access
    api_key = Column(String(255), nullable=True, unique=True, index=True)
    api_key_created_at = Column(DateTime(timezone=True), nullable=True)

    # Preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    webhook_url = Column(String(500), nullable=True)

    # Onboarding
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    # Activity tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)

    # Relationships
    projects = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    workflows = relationship(
        "Workflow",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    generations = relationship(
        "Generation",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tier={self.subscription_tier})>"

    @property
    def is_premium(self) -> bool:
        """Check if user has active premium subscription"""
        return (
            self.subscription_tier != SubscriptionTier.FREE
            and self.subscription_status == SubscriptionStatus.ACTIVE
        )

    @property
    def has_quota_remaining(self) -> bool:
        """Check if user has generation quota remaining"""
        # Free: 10/month, Creator: 100/month, Studio: unlimited
        limits = {
            SubscriptionTier.FREE: 10,
            SubscriptionTier.CREATOR: 100,
            SubscriptionTier.STUDIO: float('inf')
        }

        limit = limits.get(self.subscription_tier, 10)
        return self.monthly_generation_count < limit

    def increment_usage(self):
        """Increment monthly generation count"""
        self.monthly_generation_count += 1
        self.total_generations += 1

        # Reset counter if it's a new month
        now = datetime.utcnow()
        if (
            not self.monthly_generation_reset_at
            or now.month != self.monthly_generation_reset_at.month
        ):
            self.monthly_generation_count = 1
            self.monthly_generation_reset_at = now

    def record_login(self):
        """Record user login"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
