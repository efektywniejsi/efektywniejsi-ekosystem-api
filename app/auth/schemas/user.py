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
    created_at: str | None = None

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    enrollments_count: int = 0
    completed_courses_count: int = 0
    threads_count: int = 0
    replies_count: int = 0
    solutions_count: int = 0
    certificates_count: int = 0
    conversations_count: int = 0
    level: int = 1
    total_points: int = 0
    current_streak: int = 0
    last_activity_date: str | None = None


class UserWithStats(UserResponse):
    stats: UserStats


class UserListResponse(BaseModel):
    total: int
    users: list[UserWithStats]


class EnrollmentDetail(BaseModel):
    course_id: str
    course_title: str
    enrolled_at: str
    completed_at: str | None = None
    last_accessed_at: str | None = None


class ThreadSummary(BaseModel):
    id: str
    title: str
    category: str
    status: str
    reply_count: int
    created_at: str


class UserDetailResponse(BaseModel):
    enrollments: list[EnrollmentDetail]
    recent_threads: list[ThreadSummary]
    last_activity_at: str | None = None
