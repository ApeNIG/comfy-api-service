"""
Authentication models for API key management.

Defines user roles, API keys, and authentication-related schemas.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enum for role-based access control."""
    FREE = "free"
    PRO = "pro"
    INTERNAL = "internal"


class User(BaseModel):
    """
    User model stored in Redis.

    Redis key: cui:user:{user_id}
    """
    user_id: str = Field(..., description="Unique user identifier (UUID)")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(default=UserRole.FREE, description="User role (free, pro, internal)")

    # Quotas
    quota_daily: int = Field(..., description="Daily job quota (-1 for unlimited)")
    quota_concurrent: int = Field(..., description="Max concurrent jobs")
    rate_limit_per_minute: int = Field(..., description="Requests per minute (-1 for unlimited)")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    is_active: bool = Field(default=True, description="Whether user is active")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "role": "pro",
                "quota_daily": 100,
                "quota_concurrent": 3,
                "rate_limit_per_minute": 20,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "is_active": True
            }
        }


class APIKey(BaseModel):
    """
    API Key model stored in Redis.

    Redis key: cui:apikey:{key_hash}

    The actual key is SHA256 hashed before storage.
    """
    key_id: str = Field(..., description="Unique key identifier (UUID)")
    key_hash: str = Field(..., description="SHA256 hash of the API key")
    user_id: str = Field(..., description="Owner user ID")

    # Metadata
    name: Optional[str] = Field(None, description="Human-readable key name")
    role: UserRole = Field(..., description="Inherited from user, cached for fast lookup")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Key creation time")
    last_used_at: Optional[datetime] = Field(None, description="Last time key was used")
    expires_at: Optional[datetime] = Field(None, description="Expiration time (None = never)")

    # Status
    is_active: bool = Field(default=True, description="Whether key is active")
    revoked_at: Optional[datetime] = Field(None, description="When key was revoked")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "660e8400-e29b-41d4-a716-446655440001",
                "key_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Production API Key",
                "role": "pro",
                "created_at": "2025-01-01T00:00:00Z",
                "last_used_at": "2025-01-01T12:00:00Z",
                "expires_at": "2026-01-01T00:00:00Z",
                "is_active": True,
                "revoked_at": None
            }
        }


# Request/Response Models for API Endpoints


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    user_id: str = Field(..., description="User ID to create key for")
    name: Optional[str] = Field(None, description="Human-readable key name", max_length=100)
    expires_in_days: Optional[int] = Field(
        365,
        description="Key expiration in days (None = never expires)",
        ge=1,
        le=3650  # Max 10 years
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "My API Key",
                "expires_in_days": 365
            }
        }


class CreateAPIKeyResponse(BaseModel):
    """Response containing the newly created API key."""
    key_id: str = Field(..., description="Key ID (for revocation)")
    api_key: str = Field(..., description="The actual API key (ONLY shown once!)")
    user_id: str = Field(..., description="Owner user ID")
    name: Optional[str] = Field(None, description="Key name")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "660e8400-e29b-41d4-a716-446655440001",
                "api_key": "cui_sk_1234567890abcdef1234567890abcdef1234567890abcdef",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "My API Key",
                "role": "pro",
                "created_at": "2025-01-01T00:00:00Z",
                "expires_at": "2026-01-01T00:00:00Z"
            }
        }


class APIKeyInfo(BaseModel):
    """API key information (without the actual key)."""
    key_id: str = Field(..., description="Key ID")
    user_id: str = Field(..., description="Owner user ID")
    name: Optional[str] = Field(None, description="Key name")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Whether key is active")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "660e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "My API Key",
                "role": "pro",
                "created_at": "2025-01-01T00:00:00Z",
                "last_used_at": "2025-01-01T12:00:00Z",
                "expires_at": "2026-01-01T00:00:00Z",
                "is_active": True
            }
        }


class ListAPIKeysResponse(BaseModel):
    """Response for listing API keys."""
    user_id: str = Field(..., description="User ID")
    keys: list[APIKeyInfo] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "keys": [
                    {
                        "key_id": "660e8400-e29b-41d4-a716-446655440001",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Production Key",
                        "role": "pro",
                        "created_at": "2025-01-01T00:00:00Z",
                        "last_used_at": "2025-01-01T12:00:00Z",
                        "expires_at": "2026-01-01T00:00:00Z",
                        "is_active": True
                    }
                ],
                "total": 1
            }
        }


class RevokeAPIKeyRequest(BaseModel):
    """Request to revoke an API key."""
    key_id: str = Field(..., description="Key ID to revoke")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "660e8400-e29b-41d4-a716-446655440001"
            }
        }


class RevokeAPIKeyResponse(BaseModel):
    """Response after revoking an API key."""
    key_id: str = Field(..., description="Revoked key ID")
    revoked_at: datetime = Field(..., description="Revocation timestamp")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "660e8400-e29b-41d4-a716-446655440001",
                "revoked_at": "2025-01-01T12:00:00Z",
                "message": "API key revoked successfully"
            }
        }


class CreateUserRequest(BaseModel):
    """Request to create a new user."""
    email: str = Field(..., description="User email address")
    role: UserRole = Field(default=UserRole.FREE, description="User role")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "role": "free"
            }
        }


class CreateUserResponse(BaseModel):
    """Response after creating a user."""
    user_id: str = Field(..., description="Created user ID")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    quota_daily: int = Field(..., description="Daily job quota")
    quota_concurrent: int = Field(..., description="Max concurrent jobs")
    rate_limit_per_minute: int = Field(..., description="Rate limit per minute")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "role": "free",
                "quota_daily": 10,
                "quota_concurrent": 1,
                "rate_limit_per_minute": 5,
                "created_at": "2025-01-01T00:00:00Z"
            }
        }


class AuthenticatedUser(BaseModel):
    """
    User information extracted from a valid API key.

    Used in FastAPI dependency injection for protected routes.
    """
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    quota_daily: int = Field(..., description="Daily job quota")
    quota_concurrent: int = Field(..., description="Max concurrent jobs")
    rate_limit_per_minute: int = Field(..., description="Rate limit per minute")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "role": "pro",
                "quota_daily": 100,
                "quota_concurrent": 3,
                "rate_limit_per_minute": 20
            }
        }
