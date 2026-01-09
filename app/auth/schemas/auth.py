from typing import Literal

from pydantic import BaseModel, EmailStr

from app.auth.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """Login request schema"""

    email: EmailStr
    password: str
    role: Literal["paid", "admin"] = "paid"  # Optional, defaults to 'paid'


class TokenResponse(BaseModel):
    """
    Token response schema returned after successful login.
    Contains both access and refresh tokens plus user data.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    """Request schema for token refresh"""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Response schema for token refresh"""

    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    """Request schema for logout"""

    refresh_token: str


class LogoutResponse(BaseModel):
    """Response schema for logout"""

    message: str = "Successfully logged out"
