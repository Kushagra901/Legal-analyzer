"""
Security Utilities.
Handles token creation, validation, and password hash validations.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jwt import encode


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """
    Generate JWT access token for authentication routing.

    Args:
        subject (str | Any): Subject identifying the user.
        expires_delta (timedelta | None): Duration before token expires.

    Returns:
        str: Encrypted JWT string.
    """
    from app.core.config import settings

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
