from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.auth.services.email_service import build_password_reset_email, get_email_service
from app.core import security
from app.core.rate_limit import limiter
from app.db.session import get_db

router = APIRouter()


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


@router.post("/request-reset", response_model=MessageResponse)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = db.query(User).filter(User.email == reset_request.email).first()

    generic_message = "Jeśli podany email istnieje, link do resetowania hasła został wysłany"

    if not user:
        return MessageResponse(message=generic_message)

    if not user.is_active:
        return MessageResponse(message=generic_message)

    raw_token, hashed_token, expiry = security.generate_reset_token()

    user.password_reset_token = hashed_token
    user.password_reset_token_expires = expiry
    db.commit()

    email_service = get_email_service()
    email_message = build_password_reset_email(
        name=str(user.name), email=str(user.email), token=raw_token
    )
    await email_service.send_email(email_message)

    return MessageResponse(message=generic_message)


@router.post("/reset", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request, data: PasswordResetConfirm, db: Session = Depends(get_db)
) -> MessageResponse:
    hashed_token = security.hash_token(data.token)

    user = db.query(User).filter(User.password_reset_token == hashed_token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy lub wygasły token resetowania hasła",
        )

    if not user.password_reset_token_expires or user.password_reset_token_expires < datetime.now(
        UTC
    ):
        user.password_reset_token = None
        user.password_reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token resetowania hasła wygasł",
        )

    password_error = security.validate_password(data.new_password)
    if password_error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=password_error,
        )

    user.hashed_password = security.get_password_hash(data.new_password)

    user.password_reset_token = None
    user.password_reset_token_expires = None

    db.commit()

    return MessageResponse(message="Hasło zostało zresetowane")
