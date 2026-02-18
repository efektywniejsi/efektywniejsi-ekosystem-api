import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ImplementationPackage(Base):
    __tablename__ = "implementation_packages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    category: Mapped[str | None] = mapped_column(default=None, index=True)

    # Prices in grosz (69 PLN = 6900 groszy)
    price: Mapped[int] = mapped_column(default=0)
    original_price: Mapped[int | None] = mapped_column(default=None)
    currency: Mapped[str] = mapped_column(default="PLN")

    # Metadata
    total_time_saved: Mapped[str | None] = mapped_column(default=None)
    tools: Mapped[str] = mapped_column(default="[]")  # JSON array as string
    video_url: Mapped[str | None] = mapped_column(default=None)
    thumbnail_url: Mapped[str | None] = mapped_column(default=None)

    # Publishing
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    is_featured: Mapped[bool] = mapped_column(default=False, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    # Learning content
    estimated_hours: Mapped[int] = mapped_column(default=0)
    learning_title: Mapped[str | None] = mapped_column(default=None)
    learning_description: Mapped[str | None] = mapped_column(default=None)
    learning_thumbnail_url: Mapped[str | None] = mapped_column(default=None)

    # Sales page builder
    sales_page_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # Sales content for detail sheet (outcomes, FAQ, etc.)
    sales_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    modules = relationship(
        "Module", back_populates="implementation_package", cascade="all, delete-orphan"
    )
    processes = relationship(
        "ImplementationPackageProcess", back_populates="package", cascade="all, delete-orphan"
    )
    enrollments = relationship(
        "ImplementationPackageEnrollment", back_populates="package", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ImplementationPackage(id={self.id}, slug={self.slug}, title={self.title})>"


class ImplementationPackageProcess(Base):
    __tablename__ = "implementation_package_processes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("implementation_packages.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)

    # Relationships
    package = relationship("ImplementationPackage", back_populates="processes")

    def __repr__(self) -> str:
        return (
            f"<ImplementationPackageProcess(id={self.id}, name={self.name}, "
            f"package_id={self.package_id})>"
        )


class ImplementationPackageEnrollment(Base):
    __tablename__ = "implementation_package_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "package_id", name="uq_user_impl_package_enrollment"),
        Index("ix_impl_pkg_enrollments_user_package", "user_id", "package_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("implementation_packages.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True, default=None
    )

    enrolled_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    last_accessed_at: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    user = relationship("User", backref="implementation_package_enrollments")
    package = relationship("ImplementationPackage", back_populates="enrollments")
    order = relationship("Order", backref="implementation_package_enrollments")

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return bool(datetime.now(UTC) > self.expires_at.replace(tzinfo=UTC))

    def __repr__(self) -> str:
        return (
            f"<ImplementationPackageEnrollment(id={self.id}, user_id={self.user_id}, "
            f"package_id={self.package_id})>"
        )
