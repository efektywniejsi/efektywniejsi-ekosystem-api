import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_course_enrollment"),
        Index("ix_enrollments_user_course", "user_id", "course_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    certificate_issued_at: Mapped[datetime | None] = mapped_column(default=None)
    last_accessed_at: Mapped[datetime | None] = mapped_column(default=None)

    user = relationship("User", backref="enrollments")
    course = relationship("Course", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment(id={self.id}, user_id={self.user_id}, course_id={self.course_id})>"
