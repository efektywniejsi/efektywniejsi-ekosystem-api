import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.courses.models.course import Lesson
    from app.integrations.models.integration import Integration


class LessonIntegration(Base):
    __tablename__ = "lesson_integrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), index=True
    )
    context_note: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    integration: Mapped["Integration"] = relationship(
        "Integration", back_populates="lesson_integrations"
    )
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="integrations")

    def __repr__(self) -> str:
        return f"<LessonIntegration(lesson={self.lesson_id}, integration={self.integration_id})>"
