"""Pydantic schemas for implementation packages."""

import json
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.datetime_utils import UTCDatetime


class ImplPackageProcessResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class ImplPackageListResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    category: str | None = None
    price: int
    original_price: int | None = None
    currency: str = "PLN"
    estimated_hours: int = 0
    total_time_saved: str | None = None
    tools: list[str] = []
    video_url: str | None = None
    thumbnail_url: str | None = None
    is_published: bool = False
    is_featured: bool = False
    sort_order: int = 0
    learning_title: str | None = None
    learning_description: str | None = None
    learning_thumbnail_url: str | None = None
    created_at: UTCDatetime
    updated_at: UTCDatetime

    @field_validator("tools", mode="before")
    @classmethod
    def parse_tools(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return list(json.loads(v))
        return v

    model_config = ConfigDict(from_attributes=True)


class ImplPackageDetailResponse(ImplPackageListResponse):
    processes: list[ImplPackageProcessResponse] = []
    sales_page_sections: dict | None = None
    sales_content: dict | None = None


class ImplPackageCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1)
    category: str | None = Field(default=None, max_length=100)
    price: int = Field(default=0, ge=0)
    original_price: int | None = Field(default=None, ge=0)
    currency: str = Field(default="PLN", max_length=10)
    estimated_hours: int = Field(default=0, ge=0)
    total_time_saved: str | None = Field(default=None, max_length=100)
    tools: list[str] = Field(default_factory=list)
    video_url: str | None = Field(default=None, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    is_published: bool = False
    is_featured: bool = False
    sort_order: int = 0
    learning_title: str | None = None
    learning_description: str | None = None
    learning_thumbnail_url: str | None = None
    sales_page_sections: dict | None = None
    sales_content: dict | None = None


class ImplPackageUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    category: str | None = None
    price: int | None = Field(default=None, ge=0)
    original_price: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    estimated_hours: int | None = Field(default=None, ge=0)
    total_time_saved: str | None = None
    tools: list[str] | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    is_published: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None
    learning_title: str | None = None
    learning_description: str | None = None
    learning_thumbnail_url: str | None = None
    sales_page_sections: dict | None = None
    sales_content: dict | None = None


class ProcessCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    sort_order: int = 0


class ProcessUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    sort_order: int | None = None


class ImplPackageEnrollmentResponse(BaseModel):
    id: str
    user_id: str
    package_id: str
    user_name: str | None = None
    user_email: str
    enrolled_at: UTCDatetime
    expires_at: UTCDatetime | None = None
    is_expired: bool = False

    model_config = ConfigDict(from_attributes=True)


class ImplPackageEnrollmentListResponse(BaseModel):
    total: int
    enrollments: list[ImplPackageEnrollmentResponse]


class ImplPackageEnrollmentCreateRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    expires_at: datetime | None = None


class ImplPackageEnrollmentUpdateRequest(BaseModel):
    expires_at: datetime | None = None


class CurriculumLessonSummary(BaseModel):
    title: str
    duration_seconds: int = 0
    sort_order: int = 0


class CurriculumModuleSummary(BaseModel):
    title: str
    description: str | None = None
    sort_order: int = 0
    lessons: list[CurriculumLessonSummary] = []
    lesson_count: int = 0
    total_duration_seconds: int = 0


class PackageCurriculumResponse(BaseModel):
    modules: list[CurriculumModuleSummary] = []
    total_lessons: int = 0
    total_duration_seconds: int = 0
