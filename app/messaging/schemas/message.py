from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.messaging.schemas.conversation import ParticipantInfo


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: UUID
    sender: ParticipantInfo
    content: str
    is_system_message: bool = False
    created_at: datetime
    edited_at: datetime | None = None

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    id: UUID
    subject: str | None = None
    participants: list[ParticipantInfo]
    messages: list[MessageResponse]
    total_messages: int

    class Config:
        from_attributes = True


class UserSearchResult(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None
    role: str

    class Config:
        from_attributes = True
