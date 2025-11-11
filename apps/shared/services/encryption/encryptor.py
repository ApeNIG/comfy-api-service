"""
Token encryption service

Securely encrypts/decrypts OAuth tokens and sensitive data.
Uses Fernet (symmetric encryption) with key rotation support.

Security considerations:
- ENCRYPTION_KEY must be 32 bytes (URL-safe base64-encoded)
- Tokens are encrypted before storing in database
- Decrypted only when needed for API calls
- Supports key rotation for enhanced security
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet (symmetric encryption) which provides:
    - AES-128 encryption in CBC mode
    - HMAC for authentication
    - Timestamp for expiration
    - Built-in key derivation

    Usage:
        encryptor = EncryptionService()

        # Encrypt OAuth token
        encrypted = encryptor.encrypt("ya29.a0AfH6SMB...")
        # Returns: "gAAAAABhX..."

        # Decrypt when needed
        original = encryptor.decrypt(encrypted)
        # Returns: "ya29.a0AfH6SMB..."
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            encryption_key: Optional encryption key (defaults to settings.ENCRYPTION_KEY)
                           Must be 32 bytes URL-safe base64-encoded
        """
        key = encryption_key or settings.ENCRYPTION_KEY

        # Derive a proper Fernet key from the provided key
        self.fernet = self._create_fernet(key)

        logger.info("encryption_service_initialized")

    def _create_fernet(self, key: str) -> Fernet:
        """
        Create Fernet cipher from encryption key.

        Derives a proper 32-byte key using PBKDF2 if needed.

        Args:
            key: Encryption key from settings

        Returns:
            Fernet cipher instance
        """
        try:
            # Try to use key directly (if it's already a valid Fernet key)
            return Fernet(key.encode())
        except Exception:
            # Key is not valid Fernet format, derive one using PBKDF2HMAC
            logger.info("deriving_fernet_key_from_encryption_key")

            # Use PBKDF2HMAC to derive a 32-byte key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"comfyui-creator-salt",  # Static salt (OK for encryption key derivation)
                iterations=100000,
            )

            derived_key = kdf.derive(key.encode())
            fernet_key = base64.urlsafe_b64encode(derived_key)

            return Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt (e.g., OAuth token)

        Returns:
            Encrypted string (base64-encoded)

        Raises:
            ValueError: If plaintext is empty

        Example:
            >>> encryptor = EncryptionService()
            >>> encrypted = encryptor.encrypt("my-secret-token")
            >>> print(encrypted)
            gAAAAABhX7ZQ8b...
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            encrypted_str = encrypted_bytes.decode()

            logger.debug(
                "token_encrypted",
                plaintext_length=len(plaintext),
                encrypted_length=len(encrypted_str),
            )

            return encrypted_str

        except Exception as e:
            logger.error(
                "encryption_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Encrypted string (from encrypt method)

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If ciphertext is invalid or tampered
            ValueError: If ciphertext is empty

        Example:
            >>> encryptor = EncryptionService()
            >>> encrypted = "gAAAAABhX7ZQ8b..."
            >>> plaintext = encryptor.decrypt(encrypted)
            >>> print(plaintext)
            my-secret-token
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self.fernet.decrypt(ciphertext.encode())
            decrypted_str = decrypted_bytes.decode()

            logger.debug(
                "token_decrypted",
                ciphertext_length=len(ciphertext),
                plaintext_length=len(decrypted_str),
            )

            return decrypted_str

        except InvalidToken as e:
            logger.error(
                "decryption_failed_invalid_token",
                error=str(e),
            )
            raise

        except Exception as e:
            logger.error(
                "decryption_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt all string values in a dictionary.

        Useful for encrypting multiple tokens at once.

        Args:
            data: Dictionary with string values to encrypt

        Returns:
            Dictionary with encrypted values

        Example:
            >>> data = {
            ...     "access_token": "ya29.a0...",
            ...     "refresh_token": "1//0e...",
            ... }
            >>> encrypted = encryptor.encrypt_dict(data)
            >>> print(encrypted)
            {
                "access_token": "gAAAAABhX7ZQ8b...",
                "refresh_token": "gAAAAABhX7ZQ9c...",
            }
        """
        encrypted_data = {}

        for key, value in data.items():
            if isinstance(value, str) and value:
                encrypted_data[key] = self.encrypt(value)
            else:
                encrypted_data[key] = value

        return encrypted_data

    def decrypt_dict(self, data: dict) -> dict:
        """
        Decrypt all string values in a dictionary.

        Args:
            data: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted values

        Example:
            >>> encrypted = {
            ...     "access_token": "gAAAAABhX7ZQ8b...",
            ...     "refresh_token": "gAAAAABhX7ZQ9c...",
            ... }
            >>> decrypted = encryptor.decrypt_dict(encrypted)
            >>> print(decrypted)
            {
                "access_token": "ya29.a0...",
                "refresh_token": "1//0e...",
            }
        """
        decrypted_data = {}

        for key, value in data.items():
            if isinstance(value, str) and value:
                try:
                    decrypted_data[key] = self.decrypt(value)
                except InvalidToken:
                    # Value is not encrypted, keep as-is
                    decrypted_data[key] = value
            else:
                decrypted_data[key] = value

        return decrypted_data

    def rotate_key(self, old_key: str, new_key: str, ciphertext: str) -> str:
        """
        Re-encrypt data with a new key (for key rotation).

        Args:
            old_key: Previous encryption key
            new_key: New encryption key
            ciphertext: Data encrypted with old key

        Returns:
            Data encrypted with new key

        Example:
            >>> old_encrypted = "gAAAAABhX7ZQ8b..."
            >>> new_encrypted = encryptor.rotate_key(
            ...     old_key="old-key",
            ...     new_key="new-key",
            ...     ciphertext=old_encrypted
            ... )
        """
        # Decrypt with old key
        old_fernet = self._create_fernet(old_key)
        plaintext_bytes = old_fernet.decrypt(ciphertext.encode())

        # Encrypt with new key
        new_fernet = self._create_fernet(new_key)
        new_ciphertext = new_fernet.encrypt(plaintext_bytes)

        logger.info(
            "key_rotated",
            old_ciphertext_length=len(ciphertext),
            new_ciphertext_length=len(new_ciphertext),
        )

        return new_ciphertext.decode()


# Singleton instance for easy import
_encryptor: Optional[EncryptionService] = None


def get_encryptor() -> EncryptionService:
    """
    Get singleton EncryptionService instance.

    Returns:
        EncryptionService instance

    Usage:
        from apps.shared.services.encryption import get_encryptor

        encryptor = get_encryptor()
        encrypted = encryptor.encrypt("my-token")
    """
    global _encryptor

    if _encryptor is None:
        _encryptor = EncryptionService()

    return _encryptor


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        32-byte URL-safe base64-encoded key

    Usage:
        >>> from apps.shared.services.encryption import generate_encryption_key
        >>> key = generate_encryption_key()
        >>> print(key)
        b'WBFvJ8Zj...'

    Notes:
        - Use this in production to generate ENCRYPTION_KEY
        - Store securely in environment variables
        - Never commit to version control
    """
    return Fernet.generate_key().decode()
