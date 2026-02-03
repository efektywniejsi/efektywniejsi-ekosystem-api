import logging
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.auth.models.user_daily_activity import UserDailyActivity
from app.core import security
from app.db.session import get_db

logger = logging.getLogger(__name__)


async def get_access_token_from_cookie(
    access_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Extract and validate access token from cookie"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uwierzytelnienia",
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

    existing = (
        db.query(UserDailyActivity)
        .filter(UserDailyActivity.user_id == user.id, UserDailyActivity.date == today)
        .first()
    )
    try:
        if existing:
            existing.last_seen_at = now
        else:
            db.add(UserDailyActivity(user_id=user.id, date=today, last_seen_at=now))
        db.commit()
    except Exception:
        logger.exception("Failed to record daily activity")
        db.rollback()

    return cast(User, user)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wymagane uprawnienia administratora",
        )
    return current_user
