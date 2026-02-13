import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ThreadAttachment(Base):
    __tablename__ = "community_thread_attachments"
    __table_args__ = (
        Index("ix_thread_attachments_thread", "thread_id"),
        Index("ix_thread_attachments_uploader", "uploader_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_threads.id", ondelete="CASCADE"),
    )
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    thread = relationship("CommunityThread", back_populates="attachments")
    uploader = relationship("User", lazy="joined")
