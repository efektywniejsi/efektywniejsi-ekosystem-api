import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ThreadStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ThreadCategory(str, enum.Enum):
    PYTANIA = "pytania"
    KURSY = "kursy"
    WDROZENIA = "wdrozenia"
    SHOWCASE = "showcase"
    POMYSLY = "pomysly"
    PORADY = "porady"
    OGOLNE = "ogolne"


class CommunityThread(Base):
    __tablename__ = "community_threads"
    __table_args__ = (
        Index("ix_community_threads_category_created", "category", "created_at"),
        Index("ix_community_threads_author", "author_id"),
        Index("ix_community_threads_status", "status"),
        Index("ix_community_threads_pinned", "is_pinned"),
        Index("ix_community_threads_course", "course_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ThreadStatus.OPEN.value)
    category: Mapped[str] = mapped_column(String(20), default=ThreadCategory.PYTANIA.value)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    course_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, default=None
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("modules.id", ondelete="SET NULL"), nullable=True, default=None
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User", foreign_keys=[author_id], lazy="joined")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], lazy="joined")
    replies = relationship(
        "ThreadReply", back_populates="thread", order_by="ThreadReply.created_at"
    )
    course = relationship("Course", lazy="joined")
    module = relationship("Module", lazy="joined")
    lesson = relationship("Lesson", lazy="joined")
