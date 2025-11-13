"""
Repositories for data access

Each repository provides CRUD operations for a specific domain model.
"""

from .base import BaseRepository
from .user_repository import UserRepository
# Note: SubscriptionRepository temporarily disabled - subscription data now embedded in User model
# from .subscription_repository import SubscriptionRepository
# Note: JobRepository temporarily disabled - uses archived domain models
# from .job_repository import JobRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    # "SubscriptionRepository",
    # "JobRepository",
]
