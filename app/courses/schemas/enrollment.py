from datetime import datetime

from pydantic import BaseModel, EmailStr


class AdminEnrollmentResponse(BaseModel):
    id: str
    user_id: str
    course_id: str
    user_name: str | None = None
    user_email: str
    enrolled_at: datetime
    expires_at: datetime | None = None
    is_expired: bool = False

    class Config:
        from_attributes = True


class AdminEnrollmentListResponse(BaseModel):
    total: int
    enrollments: list[AdminEnrollmentResponse]


class AdminCreateEnrollmentRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    expires_at: datetime | None = None


class AdminUpdateEnrollmentRequest(BaseModel):
    expires_at: datetime | None = None
