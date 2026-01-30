from datetime import datetime

from pydantic import BaseModel, Field


class ProgressUpdateRequest(BaseModel):
    watched_seconds: int = Field(..., ge=0)
    last_position_seconds: int = Field(..., ge=0)
    completion_percentage: int = Field(..., ge=0, le=100)


class LessonProgressResponse(BaseModel):
    id: str
    user_id: str
    lesson_id: str
    watched_seconds: int
    last_position_seconds: int
    completion_percentage: int
    is_completed: bool
    completed_at: datetime | None = None
    last_updated_at: datetime

    class Config:
        from_attributes = True


class CourseProgressSummary(BaseModel):
    course_id: str
    total_lessons: int
    completed_lessons: int
    progress_percentage: int
    total_watch_time_seconds: int
    last_accessed_at: datetime | None = None
