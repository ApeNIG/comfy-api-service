"""
Admin endpoints for user and API key management.

Requires INTERNAL role for all operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from ..models.auth import (
    AuthenticatedUser,
    CreateUserRequest,
    CreateUserResponse,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    ListAPIKeysResponse,
    APIKeyInfo,
    RevokeAPIKeyRequest,
    RevokeAPIKeyResponse,
)
from ..services.auth_service import get_auth_service
from ..middleware.auth import require_admin
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# User Management Endpoints


@router.post(
    "/users",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="""
    Create a new user account with role-based quotas.

    **Requires:** INTERNAL role

    **Role Quotas:**
    - `free`: 10 daily jobs, 1 concurrent, 5 req/min
    - `pro`: 100 daily jobs, 3 concurrent, 20 req/min
    - `internal`: Unlimited jobs, 10 concurrent, unlimited req/min

    The user will be created with quotas appropriate for their role.
    """,
)
async def create_user(
    request: CreateUserRequest,
    admin: AuthenticatedUser = Depends(require_admin),
) -> CreateUserResponse:
    """Create a new user (admin only)."""
    auth_service = get_auth_service()

    try:
        user = await auth_service.create_user(
            email=request.email,
            role=request.role,
        )
        logger.info(f"Admin {admin.user_id} created user {user.user_id}")
        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# API Key Management Endpoints


@router.post(
    "/api-keys",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
    description="""
    Create a new API key for a user.

    **Requires:** INTERNAL role

    **Important:** The API key is only returned once in this response.
    Store it securely - you cannot retrieve it later!

    **Key Format:** `cui_sk_{43 random characters}`

    **Default Expiration:** 365 days (configurable)
    """,
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    admin: AuthenticatedUser = Depends(require_admin),
) -> CreateAPIKeyResponse:
    """Create a new API key (admin only)."""
    auth_service = get_auth_service()

    try:
        api_key_response = await auth_service.create_api_key(
            user_id=request.user_id,
            name=request.name,
            expires_in_days=request.expires_in_days,
        )
        logger.info(
            f"Admin {admin.user_id} created API key {api_key_response.key_id} "
            f"for user {request.user_id}"
        )
        return api_key_response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/api-keys/{user_id}",
    response_model=ListAPIKeysResponse,
    summary="List user's API keys",
    description="""
    List all API keys for a specific user.

    **Requires:** INTERNAL role

    Returns key metadata (IDs, names, usage stats) but NOT the actual keys.
    """,
)
async def list_api_keys(
    user_id: str,
    admin: AuthenticatedUser = Depends(require_admin),
) -> ListAPIKeysResponse:
    """List all API keys for a user (admin only)."""
    auth_service = get_auth_service()

    # Verify user exists
    user = await auth_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Get keys
    keys = await auth_service.list_user_keys(user_id)

    logger.info(f"Admin {admin.user_id} listed keys for user {user_id}")

    return ListAPIKeysResponse(
        user_id=user_id,
        keys=keys,
        total=len(keys),
    )


@router.delete(
    "/api-keys",
    response_model=RevokeAPIKeyResponse,
    summary="Revoke an API key",
    description="""
    Revoke (delete) an API key.

    **Requires:** INTERNAL role

    The key will be immediately invalidated and cannot be used for future requests.
    Requests in-flight may still complete.
    """,
)
async def revoke_api_key(
    request: RevokeAPIKeyRequest,
    admin: AuthenticatedUser = Depends(require_admin),
) -> RevokeAPIKeyResponse:
    """Revoke an API key (admin only)."""
    auth_service = get_auth_service()

    # Get key info to find owner
    key_info = await auth_service._get_key_by_id(request.key_id)
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {request.key_id} not found",
        )

    try:
        success = await auth_service.revoke_api_key(request.key_id, key_info.user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {request.key_id} not found",
            )

        revoked_at = datetime.utcnow()
        logger.info(
            f"Admin {admin.user_id} revoked API key {request.key_id} "
            f"for user {key_info.user_id}"
        )

        return RevokeAPIKeyResponse(
            key_id=request.key_id,
            revoked_at=revoked_at,
            message=f"API key {request.key_id} revoked successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# Self-Service Endpoints (for authenticated users)


@router.get(
    "/me/api-keys",
    response_model=ListAPIKeysResponse,
    tags=["users"],
    summary="List my API keys",
    description="""
    List all API keys for the authenticated user.

    **Requires:** Valid API key

    Returns key metadata but NOT the actual keys.
    """,
)
async def list_my_api_keys(
    user: AuthenticatedUser = Depends(require_admin),
) -> ListAPIKeysResponse:
    """List API keys for the current user."""
    auth_service = get_auth_service()

    keys = await auth_service.list_user_keys(user.user_id)

    return ListAPIKeysResponse(
        user_id=user.user_id,
        keys=keys,
        total=len(keys),
    )


@router.delete(
    "/me/api-keys/{key_id}",
    response_model=RevokeAPIKeyResponse,
    tags=["users"],
    summary="Revoke my API key",
    description="""
    Revoke one of your own API keys.

    **Requires:** Valid API key

    You can only revoke your own keys. Use a different key to make this request!
    """,
)
async def revoke_my_api_key(
    key_id: str,
    user: AuthenticatedUser = Depends(require_admin),
) -> RevokeAPIKeyResponse:
    """Revoke one of your own API keys."""
    auth_service = get_auth_service()

    try:
        success = await auth_service.revoke_api_key(key_id, user.user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found",
            )

        revoked_at = datetime.utcnow()
        logger.info(f"User {user.user_id} revoked their own API key {key_id}")

        return RevokeAPIKeyResponse(
            key_id=key_id,
            revoked_at=revoked_at,
            message=f"API key {key_id} revoked successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
