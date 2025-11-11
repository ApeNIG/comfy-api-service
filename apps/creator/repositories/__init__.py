"""
Repositories for data access

Each repository provides CRUD operations for a specific domain model.
"""

from .base import BaseRepository
from .user_repository import UserRepository
from .subscription_repository import SubscriptionRepository
from .job_repository import JobRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "SubscriptionRepository",
    "JobRepository",
]
