import uuid
from datetime import UTC, datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column()
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    lesson_processes: Mapped[list["LessonProcess"]] = relationship(
        "LessonProcess", back_populates="process", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Process(id={self.id}, slug={self.slug}, name={self.name})>"


# Import for type hints (avoid circular imports)
from app.processes.models.lesson_process import LessonProcess  # noqa: E402
