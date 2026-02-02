from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PublicCourseInfo(BaseModel):
    id: UUID
    title: str
    slug: str
    thumbnail_url: str | None = None
    difficulty: str
    is_completed: bool

    class Config:
        from_attributes = True


class CommunityActivity(BaseModel):
    thread_count: int
    reply_count: int
    solution_count: int


class PublicProfileResponse(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None
    role: str
    member_since: datetime
    courses: list[PublicCourseInfo] = Field(default_factory=list)
    completed_courses_count: int
    community_activity: CommunityActivity
    certificates_count: int
    level: int
    total_points: int
    current_streak: int
