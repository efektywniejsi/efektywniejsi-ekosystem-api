import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class NotificationType(str, enum.Enum):
    COURSE_UPDATE = "course_update"
    ANNOUNCEMENT = "announcement"
    DIRECT_MESSAGE = "direct_message"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    notification_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=NotificationStatus.PENDING.value)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), default=None
    )
    announcement_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("announcement_logs.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    sent_at: Mapped[datetime | None] = mapped_column(default=None)
