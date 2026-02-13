from uuid import UUID

from pydantic import BaseModel, Field

from app.core.datetime_utils import UTCDatetime


class ConversationCreate(BaseModel):
    recipient_id: UUID
    subject: str | None = Field(None, max_length=255)
    initial_message: str = Field(..., min_length=1, max_length=5000)


class ParticipantInfo(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None
    role: str

    class Config:
        from_attributes = True


class MessagePreview(BaseModel):
    content: str
    sender_name: str
    created_at: UTCDatetime


class ConversationListItem(BaseModel):
    id: UUID
    subject: str | None = None
    other_participant: ParticipantInfo
    last_message: MessagePreview | None = None
    unread_count: int = 0
    updated_at: UTCDatetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationListItem]
    total: int
