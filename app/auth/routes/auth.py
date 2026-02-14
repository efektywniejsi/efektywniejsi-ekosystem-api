import logging

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    get_refresh_token_from_cookie,
    get_validated_token_payload,
)
from app.auth.models.user import User
from app.auth.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshResponse,
)
from app.auth.schemas.user import UserResponse
from app.auth.services.token_service import token_service
from app.core import security
from app.core.encryption import decrypt_totp_secret
from app.core.rate_limit import limiter
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not security.verify_password(credentials.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Konto jest nieaktywne")

    if user.totp_enabled and user.totp_secret:
        if not credentials.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wymagany kod 2FA",
                headers={"X-2FA-Required": "true"},
            )
        totp = pyotp.TOTP(decrypt_totp_secret(user.totp_secret))
        if not totp.verify(credentials.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nieprawidłowy kod 2FA",
            )

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}

    access_token = security.create_access_token(token_data)
    refresh_token = security.create_refresh_token(token_data)

    try:
        await token_service.store_refresh_token(refresh_token, str(user.id))
    except Exception:
        logger.warning("redis_unavailable_during_login", extra={"user_id": str(user.id)})

    security.set_auth_cookies(response, access_token, refresh_token)

    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        avatar_url=user.avatar_url,
        totp_enabled=user.totp_enabled,
        password_changed_at=user.password_changed_at.isoformat()
        if user.password_changed_at
        else None,
        notification_preferences=user.notification_preferences,
    )

    return LoginResponse(user=user_response)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    db: Session = Depends(get_db),
) -> RefreshResponse:
    payload = await get_validated_token_payload(refresh_token, expected_type="refresh")

    try:
        token_data = await token_service.validate_refresh_token(refresh_token)
    except Exception:
        logger.warning("redis_unavailable_during_token_validation")
        token_data = None
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token odświeżania został unieważniony lub wygasł",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowe dane tokena",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Użytkownik nie znaleziony lub nieaktywny",
        )

    # Revoke old refresh token and issue a new one (token rotation)
    try:
        await token_service.revoke_refresh_token(refresh_token)
    except Exception:
        logger.warning("redis_unavailable_during_revoke", extra={"user_id": user_id})

    token_payload = {"sub": str(user.id), "email": user.email, "role": user.role}
    new_access_token = security.create_access_token(token_payload)
    new_refresh_token = security.create_refresh_token(token_payload)

    try:
        await token_service.store_refresh_token(new_refresh_token, str(user.id))
    except Exception:
        logger.warning("redis_unavailable_during_refresh", extra={"user_id": str(user.id)})

    security.set_auth_cookies(response, new_access_token, new_refresh_token)

    return RefreshResponse(message="Token odświeżony")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    refresh_token: str | None = Depends(get_refresh_token_from_cookie),
) -> LogoutResponse:
    if refresh_token:
        try:
            await token_service.revoke_refresh_token(refresh_token)
        except Exception:
            logger.warning("redis_unavailable_during_logout")

    security.clear_auth_cookies(response)

    return LogoutResponse(message="Wylogowano pomyślnie")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        avatar_url=current_user.avatar_url,
        totp_enabled=current_user.totp_enabled,
        password_changed_at=current_user.password_changed_at.isoformat()
        if current_user.password_changed_at
        else None,
        notification_preferences=current_user.notification_preferences,
    )
