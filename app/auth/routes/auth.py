from fastapi import APIRouter, Depends, HTTPException, Response, status
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
from app.db.session import get_db

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> LoginResponse:
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not security.verify_password(credentials.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}

    access_token = security.create_access_token(token_data)
    refresh_token = security.create_refresh_token(token_data)

    await token_service.store_refresh_token(refresh_token, str(user.id))

    security.set_auth_cookies(response, access_token, refresh_token)

    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
    )

    return LoginResponse(user=user_response)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    db: Session = Depends(get_db),
) -> RefreshResponse:
    payload = await get_validated_token_payload(refresh_token, expected_type="refresh")

    token_data = await token_service.validate_refresh_token(refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token_payload = {"sub": str(user.id), "email": user.email, "role": user.role}
    new_access_token = security.create_access_token(token_payload)

    security.update_access_cookie(response, new_access_token)

    return RefreshResponse(message="Token refreshed successfully")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    refresh_token: str | None = Depends(get_refresh_token_from_cookie),
) -> LogoutResponse:
    if refresh_token:
        await token_service.revoke_refresh_token(refresh_token)

    security.clear_auth_cookies(response)

    return LogoutResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    user_response = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
    )

    return user_response
