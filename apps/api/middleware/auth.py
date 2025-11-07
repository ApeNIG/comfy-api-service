"""
Authentication middleware for API key validation.

Provides FastAPI dependencies for:
- Optional authentication (for public endpoints)
- Required authentication (for protected endpoints)
- Role-based access control
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from ..models.auth import AuthenticatedUser, UserRole
from ..services.auth_service import get_auth_service
from ..config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication dependency.

    Returns authenticated user if valid API key provided, None otherwise.
    Does not raise errors for missing/invalid keys.

    Usage:
        @router.get("/endpoint")
        async def endpoint(user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
            if user:
                # Authenticated request
                pass
            else:
                # Anonymous request
                pass
    """
    if not settings.auth_enabled:
        # Auth disabled - return None (allow anonymous)
        return None

    if not credentials:
        # No credentials provided
        return None

    # Validate API key
    auth_service = get_auth_service()
    user = await auth_service.validate_api_key(credentials.credentials)

    if not user:
        logger.warning(f"Invalid API key attempt")
        return None

    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> AuthenticatedUser:
    """
    Required authentication dependency.

    Returns authenticated user or raises 401 Unauthorized.

    Usage:
        @router.get("/protected")
        async def protected(user: AuthenticatedUser = Depends(get_current_user)):
            # User is guaranteed to be authenticated
            pass

    Raises:
        HTTPException: 401 if no credentials or invalid API key
    """
    if not settings.auth_enabled:
        # Auth disabled - return mock user for development
        logger.warning("Authentication is disabled - returning mock user")
        return AuthenticatedUser(
            user_id="dev-user",
            email="dev@localhost",
            role=UserRole.INTERNAL,
            quota_daily=-1,
            quota_concurrent=10,
            rate_limit_per_minute=-1,
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate API key
    auth_service = get_auth_service()
    user = await auth_service.validate_api_key(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"Authenticated user {user.user_id} ({user.role.value})")
    return user


async def get_pro_user(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require PRO or INTERNAL role.

    Usage:
        @router.get("/pro-endpoint")
        async def pro_endpoint(user: AuthenticatedUser = Depends(get_pro_user)):
            # User has PRO or INTERNAL role
            pass

    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    if user.role not in [UserRole.PRO, UserRole.INTERNAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This endpoint requires PRO or INTERNAL role (you have: {user.role.value})",
        )

    return user


async def get_internal_user(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require INTERNAL role (admin access).

    Usage:
        @router.post("/admin/users")
        async def create_user(user: AuthenticatedUser = Depends(get_internal_user)):
            # User has INTERNAL (admin) role
            pass

    Raises:
        HTTPException: 403 if user doesn't have INTERNAL role
    """
    if user.role != UserRole.INTERNAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This endpoint requires INTERNAL role (you have: {user.role.value})",
        )

    return user


# Convenience alias
require_auth = get_current_user
require_pro = get_pro_user
require_admin = get_internal_user
