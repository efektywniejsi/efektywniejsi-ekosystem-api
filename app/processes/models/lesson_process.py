import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.courses.models.course import Lesson
    from app.processes.models.process import Process


class LessonProcess(Base):
    __tablename__ = "lesson_processes"
    __table_args__ = (UniqueConstraint("lesson_id", "process_id", name="uq_lesson_process"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processes.id", ondelete="CASCADE"), index=True
    )
    context_note: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    process: Mapped["Process"] = relationship("Process", back_populates="lesson_processes")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="processes")

    def __repr__(self) -> str:
        return f"<LessonProcess(lesson={self.lesson_id}, process={self.process_id})>"
