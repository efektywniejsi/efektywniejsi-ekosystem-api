from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas.code_snippet import CodeSnippet


class ProcessBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    icon: str = Field(..., min_length=1, max_length=100)
    mermaid_diagram: str | None = Field(None, max_length=10_000)
    code_snippets: list[CodeSnippet] | None = None
    is_published: bool = False
    sort_order: int = 0


class ProcessCreate(ProcessBase):
    pass


class ProcessUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    icon: str | None = Field(None, min_length=1, max_length=100)
    mermaid_diagram: str | None = Field(None, max_length=10_000)
    code_snippets: list[CodeSnippet] | None = None
    is_published: bool | None = None
    sort_order: int | None = None


class ProcessResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    icon: str
    mermaid_diagram: str | None = None
    code_snippets: list[CodeSnippet] | None = None
    is_published: bool
    sort_order: int
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProcessLessonBriefResponse(BaseModel):
    id: UUID
    title: str
    course_slug: str
    course_title: str


class ProcessDetailResponse(ProcessResponse):
    used_in_lessons: list[ProcessLessonBriefResponse] = []


class LessonProcessCreate(BaseModel):
    process_id: UUID
    context_note: str | None = None
    sort_order: int = 0


class LessonProcessResponse(BaseModel):
    id: UUID
    process: ProcessResponse
    context_note: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}
