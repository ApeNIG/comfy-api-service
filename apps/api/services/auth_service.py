"""
Authentication service for API key management.

Handles:
- User creation and management
- API key generation, validation, and revocation
- Redis-backed storage
- Role-based access control
"""

import secrets
import hashlib
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional
import logging

from ..models.auth import (
    User,
    UserRole,
    APIKey,
    APIKeyInfo,
    AuthenticatedUser,
    CreateUserResponse,
    CreateAPIKeyResponse,
)
from ..config import settings, ROLE_QUOTAS
from .redis_client import redis_client

logger = logging.getLogger(__name__)

# Redis key prefixes
USER_KEY_PREFIX = "cui:user:"
APIKEY_KEY_PREFIX = "cui:apikey:"
USER_KEYS_PREFIX = "cui:user_keys:"  # Set of key IDs for a user


class AuthService:
    """Service for authentication and API key management."""

    def __init__(self):
        """Initialize auth service."""
        self.redis = redis_client._client  # Access the underlying Redis client

    # User Management

    async def create_user(self, email: str, role: UserRole = UserRole.FREE) -> CreateUserResponse:
        """
        Create a new user with role-based quotas.

        Args:
            email: User email address
            role: User role (free, pro, internal)

        Returns:
            CreateUserResponse with user details

        Raises:
            ValueError: If user already exists
        """
        # Check if user exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # Generate user ID
        user_id = str(uuid.uuid4())

        # Get quotas for role
        quotas = ROLE_QUOTAS.get(role.value, ROLE_QUOTAS["free"])

        # Create user object
        user = User(
            user_id=user_id,
            email=email,
            role=role,
            quota_daily=quotas["quota_daily"],
            quota_concurrent=quotas["quota_concurrent"],
            rate_limit_per_minute=quotas["rate_limit_per_minute"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        # Store in Redis
        user_key = f"{USER_KEY_PREFIX}{user_id}"
        await self.redis.hset(
            user_key,
            mapping={
                "user_id": user.user_id,
                "email": user.email,
                "role": user.role.value,
                "quota_daily": str(user.quota_daily),
                "quota_concurrent": str(user.quota_concurrent),
                "rate_limit_per_minute": str(user.rate_limit_per_minute),
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "is_active": str(user.is_active),
            }
        )

        # Create email -> user_id index
        email_key = f"cui:email:{email.lower()}"
        await self.redis.set(email_key, user_id)

        logger.info(f"Created user {user_id} with role {role.value}")

        return CreateUserResponse(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            quota_daily=user.quota_daily,
            quota_concurrent=user.quota_concurrent,
            rate_limit_per_minute=user.rate_limit_per_minute,
            created_at=user.created_at,
        )

    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        user_key = f"{USER_KEY_PREFIX}{user_id}"
        user_data = await self.redis.hgetall(user_key)

        if not user_data:
            return None

        # Parse user data
        return User(
            user_id=user_data["user_id"],
            email=user_data["email"],
            role=UserRole(user_data["role"]),
            quota_daily=int(user_data["quota_daily"]),
            quota_concurrent=int(user_data["quota_concurrent"]),
            rate_limit_per_minute=int(user_data["rate_limit_per_minute"]),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            updated_at=datetime.fromisoformat(user_data["updated_at"]),
            is_active=user_data["is_active"] == "True",
        )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            User object or None if not found
        """
        email_key = f"cui:email:{email.lower()}"
        user_id = await self.redis.get(email_key)

        if not user_id:
            return None

        return await self.get_user(user_id)

    # API Key Management

    def generate_api_key(self) -> str:
        """
        Generate a cryptographically secure API key.

        Format: cui_sk_{32 random bytes in base64}

        Returns:
            API key string
        """
        # Generate 32 random bytes
        key_bytes = secrets.token_bytes(settings.api_key_length)
        # Encode to base64 URL-safe
        key_b64 = secrets.token_urlsafe(settings.api_key_length)
        # Add prefix
        return f"cui_sk_{key_b64}"

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash API key using SHA256.

        Args:
            api_key: Raw API key

        Returns:
            Hex-encoded SHA256 hash
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def create_api_key(
        self,
        user_id: str,
        name: Optional[str] = None,
        expires_in_days: Optional[int] = 365,
    ) -> CreateAPIKeyResponse:
        """
        Create a new API key for a user.

        Args:
            user_id: User ID
            name: Human-readable key name
            expires_in_days: Key expiration in days (None = never)

        Returns:
            CreateAPIKeyResponse with the API key (shown only once!)

        Raises:
            ValueError: If user not found
        """
        # Get user
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Generate API key
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        key_id = str(uuid.uuid4())

        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = None
        if expires_in_days:
            expires_at = created_at + timedelta(days=expires_in_days)

        # Create API key object
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            role=user.role,
            created_at=created_at,
            last_used_at=None,
            expires_at=expires_at,
            is_active=True,
            revoked_at=None,
        )

        # Store in Redis
        key_key = f"{APIKEY_KEY_PREFIX}{key_hash}"
        await self.redis.hset(
            key_key,
            mapping={
                "key_id": api_key_obj.key_id,
                "key_hash": api_key_obj.key_hash,
                "user_id": api_key_obj.user_id,
                "name": api_key_obj.name or "",
                "role": api_key_obj.role.value,
                "created_at": api_key_obj.created_at.isoformat(),
                "last_used_at": "",
                "expires_at": api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else "",
                "is_active": str(api_key_obj.is_active),
                "revoked_at": "",
            }
        )

        # Add TTL if expires
        if expires_at:
            ttl_seconds = int((expires_at - created_at).total_seconds())
            await self.redis.expire(key_key, ttl_seconds)

        # Add to user's key set
        user_keys_key = f"{USER_KEYS_PREFIX}{user_id}"
        await self.redis.sadd(user_keys_key, key_id)

        logger.info(f"Created API key {key_id} for user {user_id}")

        return CreateAPIKeyResponse(
            key_id=key_id,
            api_key=api_key,  # ONLY time this is returned!
            user_id=user_id,
            name=name,
            role=user.role,
            created_at=created_at,
            expires_at=expires_at,
        )

    async def validate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        """
        Validate an API key and return user information.

        Args:
            api_key: Raw API key

        Returns:
            AuthenticatedUser if valid, None otherwise
        """
        # Hash the key
        key_hash = self.hash_api_key(api_key)
        key_key = f"{APIKEY_KEY_PREFIX}{key_hash}"

        # Get key data
        key_data = await self.redis.hgetall(key_key)
        if not key_data:
            logger.warning(f"API key not found: {key_hash[:16]}...")
            return None

        # Check if active
        if key_data["is_active"] != "True":
            logger.warning(f"API key inactive: {key_data['key_id']}")
            return None

        # Check if expired
        if key_data["expires_at"]:
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.warning(f"API key expired: {key_data['key_id']}")
                return None

        # Get user
        user = await self.get_user(key_data["user_id"])
        if not user:
            logger.error(f"User not found for API key: {key_data['key_id']}")
            return None

        # Check if user is active
        if not user.is_active:
            logger.warning(f"User inactive: {user.user_id}")
            return None

        # Update last_used_at (async, no need to wait)
        await self.redis.hset(key_key, "last_used_at", datetime.utcnow().isoformat())

        logger.debug(f"API key validated for user {user.user_id}")

        return AuthenticatedUser(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            quota_daily=user.quota_daily,
            quota_concurrent=user.quota_concurrent,
            rate_limit_per_minute=user.rate_limit_per_minute,
        )

    async def list_user_keys(self, user_id: str) -> list[APIKeyInfo]:
        """
        List all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of APIKeyInfo objects
        """
        user_keys_key = f"{USER_KEYS_PREFIX}{user_id}"
        key_ids = await self.redis.smembers(user_keys_key)

        if not key_ids:
            return []

        keys = []
        for key_id in key_ids:
            # Find key by key_id (need to scan)
            # This is inefficient - in production, maintain a key_id -> key_hash index
            key_info = await self._get_key_by_id(key_id)
            if key_info:
                keys.append(key_info)

        return keys

    async def _get_key_by_id(self, key_id: str) -> Optional[APIKeyInfo]:
        """
        Get API key info by key_id.

        This is a helper that scans for the key. In production,
        maintain a key_id -> key_hash index.

        Args:
            key_id: Key ID

        Returns:
            APIKeyInfo or None
        """
        # Scan all apikey:* keys (inefficient but works for now)
        pattern = f"{APIKEY_KEY_PREFIX}*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                key_data = await self.redis.hgetall(key)
                if key_data and key_data.get("key_id") == key_id:
                    return APIKeyInfo(
                        key_id=key_data["key_id"],
                        user_id=key_data["user_id"],
                        name=key_data["name"] or None,
                        role=UserRole(key_data["role"]),
                        created_at=datetime.fromisoformat(key_data["created_at"]),
                        last_used_at=datetime.fromisoformat(key_data["last_used_at"])
                        if key_data["last_used_at"]
                        else None,
                        expires_at=datetime.fromisoformat(key_data["expires_at"])
                        if key_data["expires_at"]
                        else None,
                        is_active=key_data["is_active"] == "True",
                    )
            if cursor == 0:
                break

        return None

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: Key ID to revoke
            user_id: User ID (for authorization check)

        Returns:
            True if revoked, False if not found or not authorized

        Raises:
            ValueError: If key doesn't belong to user
        """
        # Get key info
        key_info = await self._get_key_by_id(key_id)
        if not key_info:
            return False

        # Check ownership
        if key_info.user_id != user_id:
            raise ValueError(f"API key {key_id} does not belong to user {user_id}")

        # Find the actual key in Redis (we have key_id, need key_hash)
        # Scan to find it (inefficient, but works)
        pattern = f"{APIKEY_KEY_PREFIX}*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                key_data = await self.redis.hgetall(key)
                if key_data and key_data.get("key_id") == key_id:
                    # Mark as inactive
                    revoked_at = datetime.utcnow()
                    await self.redis.hset(key, "is_active", "False")
                    await self.redis.hset(key, "revoked_at", revoked_at.isoformat())

                    # Remove from user's key set
                    user_keys_key = f"{USER_KEYS_PREFIX}{user_id}"
                    await self.redis.srem(user_keys_key, key_id)

                    logger.info(f"Revoked API key {key_id} for user {user_id}")
                    return True

            if cursor == 0:
                break

        return False


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """
    Get or create the singleton auth service instance.

    Returns:
        AuthService instance
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
