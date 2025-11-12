"""
JWT token utilities for authentication

Security Features:
- HS256 algorithm with secret key
- 7-day token expiration
- Payload validation
- Proper error handling

Usage:
    from apps.creator.utils.jwt import create_access_token, decode_access_token

    # Create token
    token = create_access_token(user_id=user.id, email=user.email)

    # Decode token
    payload = decode_access_token(token)
    if payload:
        user_id = payload["sub"]
        email = payload["email"]
"""

from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError

from config import settings


def create_access_token(user_id: UUID, email: str) -> str:
    """
    Create JWT access token for user authentication.

    Args:
        user_id: User's unique identifier
        email: User's email address

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token(user.id, user.email)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    # Calculate expiration (7 days from now)
    expires_delta = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    expire = datetime.utcnow() + expires_delta

    # Create payload
    payload = {
        "sub": str(user_id),  # Convert UUID to string
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
    }

    # Encode token
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded payload dict with 'sub' (user_id) and 'email', or None if invalid

    Example:
        >>> payload = decode_access_token(token)
        >>> if payload:
        ...     user_id = payload["sub"]
        ...     email = payload["email"]
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except InvalidTokenError:
        # Token expired, invalid signature, or malformed
        return None
    except Exception:
        # Unexpected error
        return None
