"""
Password hashing and verification using bcrypt

Security Features:
- bcrypt with configurable rounds (default: 12)
- Automatic salt generation
- Constant-time comparison
- Protection against rainbow table attacks

Usage:
    from apps.creator.utils.password import hash_password, verify_password

    # Hash a password
    hashed = hash_password("user_password_123")

    # Verify a password
    is_valid = verify_password("user_password_123", hashed)  # True
    is_valid = verify_password("wrong_password", hashed)     # False
"""

import bcrypt
from config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password as a string (bcrypt format)

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> print(hashed)
        '$2b$12$...'  # bcrypt hash format
    """
    # Convert password to bytes
    password_bytes = password.encode('utf-8')

    # Generate salt and hash
    # Use rounds from config (default: 12)
    salt = bcrypt.gensalt(rounds=settings.PASSWORD_HASH_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("correct_password")
        >>> verify_password("correct_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    try:
        # Convert to bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')

        # Check password (constant-time comparison)
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, AttributeError):
        # Invalid hash format
        return False
