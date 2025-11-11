"""
Subscription repository with custom queries
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from apps.creator.models.domain import Subscription
from apps.creator.repositories.base import BaseRepository
from apps.shared.models.enums import SubscriptionStatus, SubscriptionTier


class SubscriptionRepository(BaseRepository[Subscription]):
    """
    Subscription-specific data access operations.

    Inherits standard CRUD from BaseRepository.
    """

    def __init__(self, db: Session):
        super().__init__(db, Subscription)

    def find_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """
        Find user's active subscription.

        Args:
            user_id: User UUID

        Returns:
            Active subscription or None
        """
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
            .first()
        )

    def find_by_stripe_customer_id(
        self, stripe_customer_id: str
    ) -> Optional[Subscription]:
        """
        Find subscription by Stripe customer ID.

        Args:
            stripe_customer_id: Stripe customer ID

        Returns:
            Subscription or None
        """
        return (
            self.db.query(Subscription)
            .filter(Subscription.stripe_customer_id == stripe_customer_id)
            .first()
        )

    def find_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> Optional[Subscription]:
        """
        Find subscription by Stripe subscription ID.

        Args:
            stripe_subscription_id: Stripe subscription ID

        Returns:
            Subscription or None
        """
        return (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
            .first()
        )

    def find_expiring_trials(self, days: int = 3) -> list[Subscription]:
        """
        Find subscriptions with trials expiring soon.

        Used to send reminder emails.

        Args:
            days: Number of days before expiration

        Returns:
            List of subscriptions with expiring trials
        """
        from datetime import timedelta

        threshold = datetime.utcnow() + timedelta(days=days)

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.trial_end.isnot(None),
                Subscription.trial_end <= threshold,
                Subscription.trial_end > datetime.utcnow(),
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
            .all()
        )

    def find_ending_periods(self, days: int = 3) -> list[Subscription]:
        """
        Find subscriptions with billing periods ending soon.

        Used to reset usage counters and send renewal reminders.

        Args:
            days: Number of days before period end

        Returns:
            List of subscriptions ending soon
        """
        from datetime import timedelta

        threshold = datetime.utcnow() + timedelta(days=days)

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.current_period_end.isnot(None),
                Subscription.current_period_end <= threshold,
                Subscription.current_period_end > datetime.utcnow(),
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
            .all()
        )

    def increment_usage(
        self, subscription_id: str, credits: int = 1
    ) -> Optional[Subscription]:
        """
        Increment job and credit usage for subscription.

        Args:
            subscription_id: Subscription UUID
            credits: Number of credits consumed

        Returns:
            Updated subscription or None
        """
        subscription = self.find_by_id(subscription_id)
        if not subscription:
            return None

        subscription.increment_usage(credits)

        self.db.flush()
        self.db.refresh(subscription)
        return subscription

    def reset_usage(self, subscription_id: str) -> Optional[Subscription]:
        """
        Reset usage counters for new billing period.

        Args:
            subscription_id: Subscription UUID

        Returns:
            Updated subscription or None
        """
        subscription = self.find_by_id(subscription_id)
        if not subscription:
            return None

        subscription.reset_usage()

        self.db.flush()
        self.db.refresh(subscription)
        return subscription

    def update_stripe_info(
        self,
        subscription_id: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        stripe_price_id: str | None = None,
    ) -> Optional[Subscription]:
        """
        Update Stripe-related fields.

        Args:
            subscription_id: Subscription UUID
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            stripe_price_id: Stripe price ID

        Returns:
            Updated subscription or None
        """
        attrs = {}

        if stripe_customer_id:
            attrs["stripe_customer_id"] = stripe_customer_id

        if stripe_subscription_id:
            attrs["stripe_subscription_id"] = stripe_subscription_id

        if stripe_price_id:
            attrs["stripe_price_id"] = stripe_price_id

        return self.update(subscription_id, **attrs)

    def update_billing_period(
        self,
        subscription_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[Subscription]:
        """
        Update billing period dates.

        Args:
            subscription_id: Subscription UUID
            period_start: Period start date
            period_end: Period end date

        Returns:
            Updated subscription or None
        """
        return self.update(
            subscription_id,
            current_period_start=period_start,
            current_period_end=period_end,
        )

    def change_tier(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier,
    ) -> Optional[Subscription]:
        """
        Change subscription tier and update limits.

        Args:
            subscription_id: Subscription UUID
            new_tier: New subscription tier

        Returns:
            Updated subscription or None
        """
        # Define tier limits
        tier_limits = {
            SubscriptionTier.FREE: {
                "monthly_job_limit": 10,
                "monthly_credit_limit": 100,
            },
            SubscriptionTier.CREATOR: {
                "monthly_job_limit": 9999999,  # Effectively unlimited
                "monthly_credit_limit": 9999999,
            },
            SubscriptionTier.STUDIO: {
                "monthly_job_limit": 9999999,
                "monthly_credit_limit": 9999999,
            },
        }

        limits = tier_limits.get(new_tier, tier_limits[SubscriptionTier.FREE])

        return self.update(
            subscription_id,
            tier=new_tier.value,
            monthly_job_limit=limits["monthly_job_limit"],
            monthly_credit_limit=limits["monthly_credit_limit"],
        )

    def cancel_at_period_end(self, subscription_id: str) -> Optional[Subscription]:
        """
        Mark subscription to cancel at end of current period.

        Args:
            subscription_id: Subscription UUID

        Returns:
            Updated subscription or None
        """
        return self.update(subscription_id, cancel_at_period_end="true")

    def reactivate(self, subscription_id: str) -> Optional[Subscription]:
        """
        Reactivate a cancelled subscription.

        Args:
            subscription_id: Subscription UUID

        Returns:
            Updated subscription or None
        """
        return self.update(
            subscription_id,
            status=SubscriptionStatus.ACTIVE.value,
            cancel_at_period_end="false",
        )
