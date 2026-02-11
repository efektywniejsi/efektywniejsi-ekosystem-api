from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

IntegrationTypeValue = Literal["API", "OAuth 2.0", "MCP"]
IntegrationCategoryValue = Literal[
    "AI",
    "CRM",
    "Data Enrichment",
    "Communication",
    "Forms",
    "Payments",
    "Automation",
    "Database",
    "CDP",
    "Marketing Automation",
    "Productivity",
    "Customer Support",
    "Tools",
    "Search",
]


class IntegrationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    icon: str = Field(..., min_length=1, max_length=100)
    image_url: str | None = None  # Custom image URL (overrides icon when set)
    category: IntegrationCategoryValue
    description: str = Field(..., min_length=1)
    auth_guide: str | None = None
    official_docs_url: HttpUrl | None = None
    video_tutorial_url: HttpUrl | None = None
    is_published: bool = False
    sort_order: int = 0
    integration_types: list[IntegrationTypeValue] = []


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255)
    icon: str | None = Field(None, min_length=1, max_length=100)
    image_url: str | None = None  # Set to empty string to clear
    category: IntegrationCategoryValue | None = None
    description: str | None = None
    auth_guide: str | None = None
    official_docs_url: HttpUrl | None = None
    video_tutorial_url: HttpUrl | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    integration_types: list[IntegrationTypeValue] | None = None


class IntegrationResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    icon: str
    image_url: str | None = None
    category: str
    description: str
    official_docs_url: str | None = None
    video_tutorial_url: str | None = None
    is_published: bool
    sort_order: int
    integration_types: list[str] = []
    usage_count: int = 0  # Count of lessons using this integration
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LessonBriefResponse(BaseModel):
    id: UUID
    title: str
    course_id: UUID
    course_title: str


class IntegrationDetailResponse(IntegrationResponse):
    auth_guide: str | None = None
    used_in_lessons: list[LessonBriefResponse] = []


class IntegrationListResponse(BaseModel):
    items: list[IntegrationResponse]
    total: int


class CategoryCountResponse(BaseModel):
    category: str
    count: int


class LessonIntegrationCreate(BaseModel):
    integration_id: UUID
    context_note: str | None = None
    sort_order: int = 0


class LessonIntegrationResponse(BaseModel):
    id: UUID
    integration: IntegrationResponse
    context_note: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}
