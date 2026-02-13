import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ThreadTag(Base):
    __tablename__ = "community_thread_tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    threads = relationship(
        "CommunityThread",
        secondary="community_thread_tag_associations",
        back_populates="tags",
    )


class ThreadTagAssociation(Base):
    __tablename__ = "community_thread_tag_associations"
    __table_args__ = (
        Index("ix_thread_tag_assoc_thread", "thread_id"),
        Index("ix_thread_tag_assoc_tag", "tag_id"),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_threads.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_thread_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
