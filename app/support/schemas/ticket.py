from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.support.models.ticket import TicketCategory, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=5000)
    category: TicketCategory = TicketCategory.OTHER
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketPriorityUpdate(BaseModel):
    priority: TicketPriority


class MessageAuthor(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class TicketMessageResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author: MessageAuthor
    content: str
    is_admin_reply: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TicketListItem(BaseModel):
    id: UUID
    subject: str
    status: str
    priority: str
    category: str
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    tickets: list[TicketListItem]
    total: int


class TicketDetailResponse(BaseModel):
    id: UUID
    subject: str
    description: str
    status: str
    priority: str
    category: str
    created_at: datetime
    updated_at: datetime
    user: MessageAuthor
    messages: list[TicketMessageResponse]

    class Config:
        from_attributes = True
