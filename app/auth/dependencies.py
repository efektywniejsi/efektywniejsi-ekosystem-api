from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core import security
from app.db.session import get_db


async def get_access_token_from_cookie(
    access_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Extract and validate access token from cookie"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )
    return access_token


async def get_refresh_token_from_cookie(
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> str:
    """Extract and validate refresh token from cookie"""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
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
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type, expected {expected_type}",
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
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
