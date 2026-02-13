import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    icon: Mapped[str] = mapped_column()
    image_url: Mapped[str | None] = mapped_column(default=None)  # Custom image (overrides icon)
    category: Mapped[str] = mapped_column(index=True)
    description: Mapped[str] = mapped_column(Text)
    auth_guide: Mapped[str | None] = mapped_column(Text, default=None)
    official_docs_url: Mapped[str | None] = mapped_column(default=None)
    video_tutorial_url: Mapped[str | None] = mapped_column(default=None)
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    integration_types: Mapped[list["IntegrationType"]] = relationship(
        "IntegrationType", back_populates="integration", cascade="all, delete-orphan"
    )
    lesson_integrations: Mapped[list["LessonIntegration"]] = relationship(
        "LessonIntegration", back_populates="integration", cascade="all, delete-orphan"
    )
    process_integrations: Mapped[list["ProcessIntegration"]] = relationship(
        "ProcessIntegration", back_populates="integration", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, slug={self.slug}, name={self.name})>"


# Import for type hints (avoid circular imports)
from app.integrations.models.integration_type import IntegrationType  # noqa: E402
from app.integrations.models.lesson_integration import LessonIntegration  # noqa: E402
from app.integrations.models.process_integration import ProcessIntegration  # noqa: E402
