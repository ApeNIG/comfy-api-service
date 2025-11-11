"""
Dependency injection for Creator product

Provides repository and service instances to route handlers.

Usage in routes:
    @router.get("/users/me")
    async def get_current_user(
        current_user: User = Depends(get_current_user),
        user_repo: UserRepository = Depends(get_user_repository),
    ):
        # Route logic here
        ...
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from apps.shared.infrastructure.database import get_db
from apps.shared.infrastructure.cache import get_cache
from apps.creator.repositories import (
    UserRepository,
    SubscriptionRepository,
    JobRepository,
)
from apps.creator.models.domain import User

# Security scheme for OAuth bearer tokens
security = HTTPBearer()


# ==================== Repository Dependencies ====================


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """
    Get UserRepository instance.

    Args:
        db: Database session (injected)

    Returns:
        UserRepository instance
    """
    return UserRepository(db)


def get_subscription_repository(
    db: Session = Depends(get_db),
) -> SubscriptionRepository:
    """
    Get SubscriptionRepository instance.

    Args:
        db: Database session (injected)

    Returns:
        SubscriptionRepository instance
    """
    return SubscriptionRepository(db)


def get_job_repository(db: Session = Depends(get_db)) -> JobRepository:
    """
    Get JobRepository instance.

    Args:
        db: Database session (injected)

    Returns:
        JobRepository instance
    """
    return JobRepository(db)


# ==================== Authentication Dependencies ====================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository),
    cache = Depends(get_cache),
) -> User:
    """
    Get current authenticated user from OAuth token.

    This dependency:
    1. Extracts bearer token from Authorization header
    2. Validates token with Google OAuth
    3. Fetches user from database
    4. Caches user for subsequent requests

    Args:
        credentials: HTTP bearer token (injected)
        user_repo: User repository (injected)
        cache: Redis cache (injected)

    Returns:
        Authenticated User instance

    Raises:
        HTTPException: 401 if token invalid or user not found

    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials

    # Check cache first (5-minute TTL)
    cache_key = f"user_token:{token[:16]}"  # Use token prefix as key
    cached_user_id = cache.get(cache_key)

    if cached_user_id:
        user = user_repo.find_by_id(cached_user_id)
        if user and user.is_active:
            return user

    # Validate token with Google OAuth
    # TODO: Implement actual Google token validation
    # For now, we'll use a simple lookup by access token
    # In production, you'd call Google's tokeninfo endpoint

    # Simplified token validation (replace with actual OAuth validation)
    user = user_repo.find_one_by(google_access_token=token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Cache user ID for 5 minutes
    cache.setex(cache_key, 300, str(user.id))

    return user


async def get_current_user_optional(
    user_repo: UserRepository = Depends(get_user_repository),
    cache = Depends(get_cache),
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> User | None:
    """
    Get current user if authenticated, otherwise return None.

    This is for pages that work both logged in and logged out (e.g., landing page).

    Args:
        user_repo: User repository (injected)
        cache: Redis cache (injected)
        credentials: Optional HTTP bearer token (injected)

    Returns:
        User if authenticated, None otherwise

    Usage:
        @router.get("/home")
        async def home(user: User | None = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Welcome back, {user.full_name}!"}
            return {"message": "Welcome! Please sign up."}
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Check cache first
    cache_key = f"user_token:{token[:16]}"
    cached_user_id = cache.get(cache_key)

    if cached_user_id:
        user = user_repo.find_by_id(cached_user_id)
        if user and user.is_active:
            return user

    # Validate token
    user = user_repo.find_one_by(google_access_token=token)

    if user and user.is_active:
        # Cache user ID
        cache.setex(cache_key, 300, str(user.id))
        return user

    return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify they are active.

    Args:
        current_user: Current user (injected)

    Returns:
        Active user

    Raises:
        HTTPException: 403 if user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_user_with_subscription(
    current_user: User = Depends(get_current_user),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
) -> tuple[User, "Subscription | None"]:
    """
    Get current user with their subscription.

    Args:
        current_user: Current user (injected)
        subscription_repo: Subscription repository (injected)

    Returns:
        Tuple of (user, subscription)
    """
    subscription = subscription_repo.find_by_user_id(current_user.id)
    return current_user, subscription


async def require_subscription(
    current_user: User = Depends(get_current_user),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
) -> "Subscription":
    """
    Require user to have an active subscription.

    Args:
        current_user: Current user (injected)
        subscription_repo: Subscription repository (injected)

    Returns:
        Active subscription

    Raises:
        HTTPException: 403 if no active subscription
    """
    subscription = subscription_repo.find_by_user_id(current_user.id)

    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required",
        )

    return subscription


async def require_paid_subscription(
    current_user: User = Depends(get_current_user),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
) -> "Subscription":
    """
    Require user to have a paid subscription (Creator or Studio tier).

    Args:
        current_user: Current user (injected)
        subscription_repo: Subscription repository (injected)

    Returns:
        Paid subscription

    Raises:
        HTTPException: 403 if no paid subscription
    """
    from apps.shared.models.enums import SubscriptionTier

    subscription = subscription_repo.find_by_user_id(current_user.id)

    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required",
        )

    if subscription.tier == SubscriptionTier.FREE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Paid subscription required (Creator or Studio tier)",
        )

    return subscription


async def check_job_quota(
    current_user: User = Depends(get_current_user),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
) -> "Subscription":
    """
    Check if user has remaining job quota.

    Args:
        current_user: Current user (injected)
        subscription_repo: Subscription repository (injected)

    Returns:
        Subscription with available quota

    Raises:
        HTTPException: 429 if quota exceeded
    """
    subscription = subscription_repo.find_by_user_id(current_user.id)

    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required",
        )

    if not subscription.can_run_job:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly job quota exceeded. Upgrade to Creator or Studio tier for unlimited jobs.",
            headers={"Retry-After": "86400"},  # Retry after 1 day
        )

    return subscription


# ==================== Admin Dependencies ====================


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require user to be an admin.

    Args:
        current_user: Current user (injected)

    Returns:
        Admin user

    Raises:
        HTTPException: 403 if not admin
    """
    from apps.shared.models.enums import UserRole

    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user
