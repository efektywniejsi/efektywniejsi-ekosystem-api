from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.auth.services.email_service import build_password_reset_email, get_email_service
from app.core import security
from app.db.session import get_db

router = APIRouter()


class PasswordResetRequest(BaseModel):
    """Request schema for password reset"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirmation schema for password reset"""

    token: str
    new_password: str


class MessageResponse(BaseModel):
    """Generic message response"""

    message: str


@router.post("/request-reset", response_model=MessageResponse)
async def request_password_reset(
    request: PasswordResetRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Request a password reset link.

    - Finds user by email
    - Generates secure reset token
    - Stores hashed token in database
    - Sends reset link via email

    Security: Always returns same message to prevent user enumeration.

    Args:
        request: Email address
        db: Database session

    Returns:
        Generic success message
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    # Always return same message (prevent user enumeration)
    generic_message = "If the email exists, a password reset link has been sent"

    if not user:
        # User doesn't exist, but return same message
        return MessageResponse(message=generic_message)

    if not user.is_active:
        # Inactive user, but return same message
        return MessageResponse(message=generic_message)

    # Generate reset token
    raw_token, hashed_token, expiry = security.generate_reset_token()

    # Store hashed token in database
    user.password_reset_token = hashed_token
    user.password_reset_token_expires = expiry
    db.commit()

    # Send email
    email_service = get_email_service()
    email_message = build_password_reset_email(
        name=user.name, email=user.email, token=raw_token
    )
    await email_service.send_email(email_message)

    return MessageResponse(message=generic_message)


@router.post("/reset", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Reset password using a valid token.

    - Validates token and expiry
    - Updates user password
    - Clears reset token from database

    Args:
        request: Reset token and new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTP 400: If token is invalid or expired
    """
    # Hash the provided token
    hashed_token = security.hash_token(request.token)

    # Find user with this token
    user = db.query(User).filter(User.password_reset_token == hashed_token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    # Check if token has expired
    if not user.password_reset_token_expires or user.password_reset_token_expires < datetime.utcnow():
        # Clear expired token
        user.password_reset_token = None
        user.password_reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    # Validate new password (add more validation as needed)
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long",
        )

    # Update password
    user.hashed_password = security.get_password_hash(request.new_password)

    # Clear reset token
    user.password_reset_token = None
    user.password_reset_token_expires = None

    db.commit()

    return MessageResponse(message="Password successfully reset")
