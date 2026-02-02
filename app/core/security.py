import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import Response
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    return str(pwd_context.hash(password))


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "access"})
    encoded_jwt: str = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        }
    )
    encoded_jwt: str = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_reset_token() -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(32)
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    expiry = datetime.now(UTC) + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    return raw_token, hashed_token, expiry


def _cookie_samesite() -> Literal["lax", "none"]:
    """Return SameSite policy: 'none' for cross-site production, 'lax' for same-site/dev."""
    return "lax" if settings.DEBUG else "none"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly cookies for authentication tokens"""
    is_secure = not settings.DEBUG
    samesite = _cookie_samesite()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite=samesite,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite=samesite,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def update_access_cookie(response: Response, access_token: str) -> None:
    """Update only the access token cookie (used in refresh endpoint)"""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite=_cookie_samesite(),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies on logout"""
    samesite = _cookie_samesite()
    response.delete_cookie("access_token", samesite=samesite, secure=not settings.DEBUG)
    response.delete_cookie("refresh_token", samesite=samesite, secure=not settings.DEBUG)
