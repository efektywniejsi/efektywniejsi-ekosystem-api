import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class LessonStatus(str, enum.Enum):
    UNAVAILABLE = "unavailable"
    IN_PREPARATION = "in_preparation"
    AVAILABLE = "available"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    thumbnail_url: Mapped[str | None] = mapped_column(default=None)
    difficulty: Mapped[str] = mapped_column(default="beginner")
    estimated_hours: Mapped[int] = mapped_column(default=0)
    is_published: Mapped[bool] = mapped_column(default=False)
    is_featured: Mapped[bool] = mapped_column(default=False)
    category: Mapped[str | None] = mapped_column(default=None, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    content_type: Mapped[str] = mapped_column(default="course", index=True)
    learning_title: Mapped[str | None] = mapped_column(default=None)
    learning_description: Mapped[str | None] = mapped_column(default=None)
    learning_thumbnail_url: Mapped[str | None] = mapped_column(default=None)
    sales_page_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    certificates = relationship(
        "Certificate", back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, slug={self.slug}, title={self.title})>"


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Module(id={self.id}, title={self.title}, course_id={self.course_id})>"


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    mux_playback_id: Mapped[str | None] = mapped_column(default=None, index=True)
    mux_asset_id: Mapped[str | None] = mapped_column(default=None, index=True)
    duration_seconds: Mapped[int] = mapped_column(default=0)
    is_preview: Mapped[bool] = mapped_column(default=False)
    status: Mapped[LessonStatus] = mapped_column(
        Enum(LessonStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=LessonStatus.AVAILABLE,
    )
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    module = relationship("Module", back_populates="lessons")
    progress_records = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )
    attachments = relationship("Attachment", back_populates="lesson", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, title={self.title}, module_id={self.module_id})>"
