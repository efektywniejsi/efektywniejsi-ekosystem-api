import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, enum.Enum):
    PAYMENT = "payment"
    ACCESS = "access"
    TECHNICAL = "technical"
    OTHER = "other"


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_user_status", "user_id", "status"),
        Index("ix_support_tickets_status_priority", "status", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=TicketStatus.OPEN.value)
    priority: Mapped[str] = mapped_column(String(20), default=TicketPriority.MEDIUM.value)
    category: Mapped[str] = mapped_column(String(20), default=TicketCategory.OTHER.value)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", lazy="joined")
    messages = relationship(
        "TicketMessage", back_populates="ticket", order_by="TicketMessage.created_at"
    )
