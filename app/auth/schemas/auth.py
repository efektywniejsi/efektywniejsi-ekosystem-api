from typing import Literal

from pydantic import BaseModel, EmailStr

from app.auth.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: Literal["paid", "admin"] = "paid"  # Optional, defaults to 'paid'


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"
