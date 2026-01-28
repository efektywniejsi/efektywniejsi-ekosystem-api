from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCourseProgress(BaseModel):
    user_id: str
    user_name: str | None
    user_email: str
    progress_percentage: int  # 0-100
    completed_lessons: int
    total_lessons: int
    session_count: int  # distinct days with activity
    first_activity_at: datetime | None
    last_activity_at: datetime | None
    total_watch_time_seconds: int
    is_completed: bool


class UserProgressListResponse(BaseModel):
    total: int
    users: list[UserCourseProgress]


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
