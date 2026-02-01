from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.community.models.thread import ThreadCategory


class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10, max_length=5000)
    category: ThreadCategory = ThreadCategory.PYTANIA
    course_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None


class ThreadUpdate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10, max_length=5000)


class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class ReplyUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class AuthorInfo(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class ReplyResponse(BaseModel):
    id: UUID
    thread_id: UUID
    author: AuthorInfo
    content: str
    is_solution: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ThreadListItem(BaseModel):
    id: UUID
    title: str
    status: str
    category: str
    is_pinned: bool
    reply_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    author: AuthorInfo
    last_activity: datetime
    course_title: str | None = None
    module_title: str | None = None
    lesson_title: str | None = None

    class Config:
        from_attributes = True


class ThreadListResponse(BaseModel):
    threads: list[ThreadListItem]
    total: int


class ThreadDetailResponse(BaseModel):
    id: UUID
    title: str
    content: str
    status: str
    category: str
    is_pinned: bool
    reply_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    author: AuthorInfo
    resolved_by: AuthorInfo | None = None
    resolved_at: datetime | None = None
    replies: list[ReplyResponse]
    course_title: str | None = None
    module_title: str | None = None
    lesson_title: str | None = None

    class Config:
        from_attributes = True
