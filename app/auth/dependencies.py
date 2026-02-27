from datetime import UTC, datetime
from typing import Annotated, cast

import structlog
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.auth.models.user_daily_activity import UserDailyActivity
from app.core import security
from app.db.session import get_db

logger = structlog.get_logger(__name__)

_activity_cache: dict[str, float] = {}  # "user_id:date" -> last write timestamp
_ACTIVITY_DEBOUNCE_SECONDS = 300  # write to DB at most once per 5 min per user


async def get_access_token_from_cookie(
    access_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Extract and validate access token from cookie"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak uwierzytelnienia",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return access_token


async def get_refresh_token_from_cookie(
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Extract and validate refresh token from cookie"""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak tokena odświeżania",
        )
    return refresh_token


async def get_validated_token_payload(
    token: str,
    expected_type: str = "access",
) -> dict:
    """Decode and validate JWT token"""
    payload = security.decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nie udało się zweryfikować danych uwierzytelniających",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Nieprawidłowy typ tokena, oczekiwano {expected_type}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    access_token: str = Depends(get_access_token_from_cookie),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from access token"""
    payload = await get_validated_token_payload(access_token, expected_type="access")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nie udało się zweryfikować danych uwierzytelniających",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Użytkownik nie znaleziony",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest nieaktywne",
        )

    now = datetime.now(UTC)
    today = now.date()
    cache_key = f"{user.id}:{today}"
    last_write = _activity_cache.get(cache_key, 0)

    if now.timestamp() - last_write > _ACTIVITY_DEBOUNCE_SECONDS:
        existing = (
            db.query(UserDailyActivity)
            .filter(
                UserDailyActivity.user_id == user.id,
                UserDailyActivity.date == today,
            )
            .first()
        )
        try:
            if existing:
                existing.last_seen_at = now
            else:
                db.add(UserDailyActivity(user_id=user.id, date=today, last_seen_at=now))
            db.commit()
            _activity_cache[cache_key] = now.timestamp()
        except Exception:
            logger.exception("Failed to record daily activity")
            db.rollback()

    return cast(User, user)


async def get_optional_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> User | None:
    """Try to get current user from cookie, return None if not authenticated."""
    if not access_token:
        return None

    try:
        payload = await get_validated_token_payload(access_token, expected_type="access")
    except HTTPException:
        return None

    user_id: str | None = payload.get("sub")
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None

    return cast(User, user)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wymagane uprawnienia administratora",
        )
    return current_user
