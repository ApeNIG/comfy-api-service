"""
Subscription domain model

Represents a user's subscription plan with Stripe integration.
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from apps.shared.models.base import BaseModel
from apps.shared.models.enums import SubscriptionTier, SubscriptionStatus


class Subscription(BaseModel):
    """
    User subscription with Stripe billing.

    Relationships:
        - user: Many-to-one with User
    """

    __tablename__ = "subscriptions"

    # Foreign Keys
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Subscription Details
    tier = Column(
        String(50),
        default=SubscriptionTier.FREE.value,
        nullable=False,
        index=True,
    )
    status = Column(
        String(50),
        default=SubscriptionStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    # Billing Period
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(String(50), default="false", nullable=False)

    # Stripe Integration
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Usage Limits (based on tier)
    monthly_job_limit = Column(Integer, default=10, nullable=False)  # Jobs per month
    monthly_credit_limit = Column(Integer, default=100, nullable=False)  # Credits per month

    # Usage Tracking (resets monthly)
    jobs_used_this_period = Column(Integer, default=0, nullable=False)
    credits_used_this_period = Column(Integer, default=0, nullable=False)

    # Pricing (stored for historical records)
    price_amount = Column(Numeric(10, 2), nullable=True)  # e.g., 29.99
    price_currency = Column(String(3), default="USD", nullable=False)

    # Trial
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)

    # Timestamps (inherited from BaseModel)
    # id, created_at, updated_at

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status == SubscriptionStatus.ACTIVE.value

    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end

    @property
    def can_run_job(self) -> bool:
        """Check if user has job quota remaining."""
        if self.tier == SubscriptionTier.FREE.value:
            return self.jobs_used_this_period < self.monthly_job_limit
        # Creator and Studio tiers have unlimited jobs
        return True

    @property
    def remaining_jobs(self) -> int | None:
        """Get remaining jobs for this period (None = unlimited)."""
        if self.tier == SubscriptionTier.FREE.value:
            return max(0, self.monthly_job_limit - self.jobs_used_this_period)
        return None  # Unlimited

    @property
    def remaining_credits(self) -> int | None:
        """Get remaining credits for this period (None = unlimited)."""
        if self.tier == SubscriptionTier.FREE.value:
            return max(0, self.monthly_credit_limit - self.credits_used_this_period)
        return None  # Unlimited

    def increment_usage(self, credits: int = 1) -> None:
        """
        Increment job and credit usage.

        Args:
            credits: Number of credits consumed (default 1)
        """
        self.jobs_used_this_period += 1
        self.credits_used_this_period += credits

    def reset_usage(self) -> None:
        """Reset usage counters (called at period end)."""
        self.jobs_used_this_period = 0
        self.credits_used_this_period = 0
