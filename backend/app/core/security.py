"""
Security Module

Handles password hashing, JWT token generation/validation, and API key encryption.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# -----------------------------------------------------------------------------
# Password Hashing
# -----------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password

    Note:
        Bcrypt has a 72-byte limit. Passwords longer than 72 bytes
        are truncated to the first 72 bytes before hashing.
    """
    # Truncate password to 72 bytes if needed (bcrypt limit)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')

    return pwd_context.hash(password)


# -----------------------------------------------------------------------------
# JWT Token Handling
# -----------------------------------------------------------------------------
def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode (typically user_id)
        expires_delta: Optional custom expiration

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Payload data to encode

    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        dict: Decoded token payload

    Raises:
        jwt.JWTError: If token is invalid or expired
    """
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


# -----------------------------------------------------------------------------
# API Key Encryption
# -----------------------------------------------------------------------------
def get_encryption_key() -> bytes:
    """
    Get the encryption key for sensitive data.

    Returns:
        bytes: 32-byte encryption key
    """
    import base64

    key = settings.encryption_key
    if not key:
        # Generate key for development (should not happen in prod)
        key = Fernet.generate_key().decode()
    return base64.urlsafe_b64decode(key.encode())


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data (API keys, secrets).

    Args:
        data: Plain text sensitive data

    Returns:
        str: Encrypted data (base64 encoded)
    """
    from cryptography.fernet import Fernet

    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.encrypt(data.encode()).decode()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data.

    Args:
        encrypted_data: Encrypted data (base64 encoded)

    Returns:
        str: Decrypted plain text
    """
    from cryptography.fernet import Fernet

    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data.encode()).decode()
