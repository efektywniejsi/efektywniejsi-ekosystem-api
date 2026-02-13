import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course_certificate"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    certificate_code: Mapped[str] = mapped_column(unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    file_path: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    user = relationship("User", backref="certificates")
    course = relationship("Course", back_populates="certificates")

    def __repr__(self) -> str:
        return f"<Certificate(id={self.id}, code={self.certificate_code}, user_id={self.user_id}, course_id={self.course_id})>"  # noqa: E501
