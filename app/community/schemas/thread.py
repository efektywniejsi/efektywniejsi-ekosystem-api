from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.community.models.thread import ThreadCategory
from app.core.datetime_utils import UTCDatetime


class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10, max_length=5000)
    category: ThreadCategory = ThreadCategory.POMOC
    course_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=5)


class ThreadUpdate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10, max_length=5000)
    course_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    clear_course_context: bool = False


class AdminThreadUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    content: str | None = Field(None, min_length=10, max_length=5000)
    category: ThreadCategory | None = None
    is_pinned: bool | None = None


class ThreadMoveRequest(BaseModel):
    category: ThreadCategory


BulkActionType = Literal["close", "reopen", "delete", "pin", "unpin"]


class BulkActionRequest(BaseModel):
    thread_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    action: BulkActionType


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
    created_at: UTCDatetime
    updated_at: UTCDatetime | None = None

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
    created_at: UTCDatetime
    updated_at: UTCDatetime
    author: AuthorInfo
    last_activity: UTCDatetime
    course_title: str | None = None
    module_title: str | None = None
    lesson_title: str | None = None
    tags: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ThreadListResponse(BaseModel):
    threads: list[ThreadListItem]
    total: int


class ThreadAttachmentResponse(BaseModel):
    id: UUID
    file_name: str
    file_size_bytes: int
    mime_type: str
    created_at: UTCDatetime

    class Config:
        from_attributes = True


class ThreadDetailResponse(BaseModel):
    id: UUID
    title: str
    content: str
    status: str
    category: str
    is_pinned: bool
    reply_count: int
    view_count: int
    created_at: UTCDatetime
    updated_at: UTCDatetime
    author: AuthorInfo
    resolved_by: AuthorInfo | None = None
    resolved_at: UTCDatetime | None = None
    replies: list[ReplyResponse]
    course_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    course_title: str | None = None
    module_title: str | None = None
    lesson_title: str | None = None
    tags: list[str] = Field(default_factory=list)
    attachments: list[ThreadAttachmentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TopAuthorItem(BaseModel):
    id: str
    name: str
    thread_count: int


class AdminStatsResponse(BaseModel):
    total_threads: int
    open_threads: int
    resolved_threads: int
    closed_threads: int
    total_replies: int
    threads_today: int
    replies_today: int
    category_counts: dict[str, int]
    top_authors: list[TopAuthorItem]


class UserActivityItem(BaseModel):
    user_id: UUID
    user_name: str
    thread_count: int
    reply_count: int
    solution_count: int
    last_activity: UTCDatetime | None = None


class UserActivityResponse(BaseModel):
    users: list[UserActivityItem]
    total: int


class BulkActionResponse(BaseModel):
    affected: int
    action: str
