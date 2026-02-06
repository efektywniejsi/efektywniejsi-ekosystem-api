from datetime import date

from pydantic import BaseModel, Field

from app.core.datetime_utils import UTCDatetime


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
    completed_at: UTCDatetime | None = None
    last_updated_at: UTCDatetime

    class Config:
        from_attributes = True


class LessonProgressInCourse(BaseModel):
    """Simplified lesson progress for course summary."""

    lesson_id: str
    watched_seconds: int = 0
    last_position_seconds: int = 0
    completion_percentage: int = 0
    is_completed: bool = False
    completed_at: UTCDatetime | None = None
    last_updated_at: UTCDatetime | None = None


class CourseProgressSummary(BaseModel):
    course_id: str
    total_lessons: int
    completed_lessons: int
    progress_percentage: int
    total_watch_time_seconds: int
    last_accessed_at: UTCDatetime | None = None
    lessons: list[LessonProgressInCourse] = []


class WeeklyStatsResponse(BaseModel):
    week_start: date
    week_end: date
    active_days: int
    learning_minutes: int
    lessons_completed: int
    points_earned: int
    current_streak: int
    active_dates: list[date]
    longest_streak: int


class MonthlyActivityResponse(BaseModel):
    year: int
    month: int
    active_dates: list[date]
