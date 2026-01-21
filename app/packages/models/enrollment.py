import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PackageEnrollment(Base):
    __tablename__ = "package_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "package_id", name="uq_user_package_enrollment"),
        Index("ix_package_enrollments_user_package", "user_id", "package_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True, default=None
    )

    enrolled_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_accessed_at: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    user = relationship("User", backref="package_enrollments")
    package = relationship("Package", back_populates="enrollments")
    order = relationship("Order", backref="package_enrollments")

    def __repr__(self) -> str:
        return f"<PackageEnrollment(id={self.id}, user_id={self.user_id}, package_id={self.package_id})>"
