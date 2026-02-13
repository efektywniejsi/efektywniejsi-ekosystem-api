from pydantic import BaseModel, EmailStr

from app.auth.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class LoginResponse(BaseModel):
    user: UserResponse


class RefreshResponse(BaseModel):
    message: str = "Token refreshed successfully"


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"
