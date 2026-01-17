import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column()
    file_name: Mapped[str] = mapped_column()
    file_path: Mapped[str] = mapped_column()
    file_size_bytes: Mapped[int] = mapped_column()
    mime_type: Mapped[str] = mapped_column()
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, title={self.title}, lesson_id={self.lesson_id})>"
