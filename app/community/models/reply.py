import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ThreadReply(Base):
    __tablename__ = "thread_replies"
    __table_args__ = (
        Index("ix_thread_replies_thread", "thread_id"),
        Index("ix_thread_replies_author", "author_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_threads.id", ondelete="CASCADE")
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    is_solution: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    thread = relationship("CommunityThread", back_populates="replies")
    author = relationship("User", lazy="joined")
