"""
Shared enums used across the application
"""

from enum import Enum


class JobStatus(str, Enum):
    """Job processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubscriptionTier(str, Enum):
    """User subscription tiers"""
    FREE = "free"
    CREATOR = "creator"
    STUDIO = "studio"


class SubscriptionStatus(str, Enum):
    """Stripe subscription status"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class UserRole(str, Enum):
    """User roles for permissions"""
    USER = "user"
    ADMIN = "admin"


class StorageProvider(str, Enum):
    """Storage backend types"""
    GOOGLE_DRIVE = "google_drive"
    MINIO = "minio"
    S3 = "s3"


class NotificationType(str, Enum):
    """Email notification types"""
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    QUOTA_WARNING = "quota_warning"
    PAYMENT_FAILED = "payment_failed"
    WELCOME = "welcome"
