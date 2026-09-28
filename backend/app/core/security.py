"""
security helpers for passwords and JWT authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """convert a plain password into a bcrypt hash."""

    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt)

    return password_hash.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """check whether a plain password matches its stored hash."""

    password_bytes = password.encode("utf-8")
    password_hash_bytes = password_hash.encode("utf-8")

    return bcrypt.checkpw(password_bytes, password_hash_bytes)


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """create a signed JWT containing the user ID and role."""

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.jwt_expire_minutes
        )

    expiration_time = datetime.now(timezone.utc) + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expiration_time,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """decode a JWT or raise a clear error when it is invalid."""

    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as error:
        raise ValueError("the access token has expired") from error
    except jwt.InvalidTokenError as error:
        raise ValueError("the access token is invalid") from error