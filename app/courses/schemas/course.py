from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str
    thumbnail_url: str | None = None
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    estimated_hours: int = Field(default=0, ge=0)
    is_published: bool = False
    is_featured: bool = False
    category: str | None = None
    sort_order: int = 0


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    slug: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    thumbnail_url: str | None = None
    difficulty: Literal["beginner", "intermediate", "advanced"] | None = None
    estimated_hours: int | None = Field(None, ge=0)
    is_published: bool | None = None
    is_featured: bool | None = None
    category: str | None = None
    sort_order: int | None = None


class CourseResponse(CourseBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModuleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    sort_order: int = 0


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    sort_order: int | None = None


class ModuleResponse(ModuleBase):
    id: str
    course_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    mux_playback_id: str = Field(..., min_length=1, max_length=255)
    mux_asset_id: str | None = Field(None, max_length=255)
    duration_seconds: int = Field(default=0, ge=0)
    is_preview: bool = False
    sort_order: int = 0


class LessonCreate(LessonBase):
    pass


class LessonUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    mux_playback_id: str | None = Field(None, min_length=1, max_length=255)
    mux_asset_id: str | None = Field(None, max_length=255)
    duration_seconds: int | None = Field(None, ge=0)
    is_preview: bool | None = None
    sort_order: int | None = None


class LessonResponse(LessonBase):
    id: str
    module_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LessonWithProgressResponse(LessonResponse):
    watched_seconds: int = 0
    last_position_seconds: int = 0
    completion_percentage: int = 0
    is_completed: bool = False


class ModuleWithLessonsResponse(ModuleResponse):
    lessons: list[LessonResponse] = []


class CourseDetailResponse(CourseResponse):
    modules: list[ModuleWithLessonsResponse] = []
    total_lessons: int = 0
    total_duration_seconds: int = 0


class CourseWithProgressResponse(CourseResponse):
    completed_lessons: int = 0
    total_lessons: int = 0
    progress_percentage: int = 0
    enrolled_at: datetime | None = None
    last_accessed_at: datetime | None = None


class EnrollmentResponse(BaseModel):
    id: str
    user_id: str
    course_id: str
    enrolled_at: datetime
    completed_at: datetime | None = None
    certificate_issued_at: datetime | None = None
    last_accessed_at: datetime | None = None

    class Config:
        from_attributes = True


class EnrollmentWithCourseResponse(EnrollmentResponse):
    course: CourseResponse
