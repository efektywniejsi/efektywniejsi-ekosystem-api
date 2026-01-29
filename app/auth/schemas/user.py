from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    avatar_url: str | None = None
    totp_enabled: bool = False
    password_changed_at: str | None = None
    notification_preferences: dict | None = None

    class Config:
        from_attributes = True
