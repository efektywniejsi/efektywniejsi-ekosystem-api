"""Bundle models for course-package combinations."""

import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BundleCourseItem(Base):
    """Link table: Bundle → Course."""

    __tablename__ = "bundle_course_items"
    __table_args__ = (
        UniqueConstraint("bundle_id", "course_id", name="uq_bundle_course"),
        Index("ix_bundle_course_items_bundle_course", "bundle_id", "course_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(default=0)

    # Relationships
    bundle = relationship("Package", foreign_keys=[bundle_id], back_populates="course_items")
    course = relationship("Course", foreign_keys=[course_id])

    def __repr__(self) -> str:
        return f"<BundleCourseItem(bundle_id={self.bundle_id}, course_id={self.course_id})>"
