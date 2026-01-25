import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    category: Mapped[str] = mapped_column(index=True)

    # Prices in grosz (69 PLN → 6900 groszy)
    price: Mapped[int] = mapped_column()
    original_price: Mapped[int | None] = mapped_column(default=None)
    currency: Mapped[str] = mapped_column(default="PLN")

    # Metadata
    difficulty: Mapped[str] = mapped_column()
    total_time_saved: Mapped[str | None] = mapped_column(default=None)
    tools: Mapped[str] = mapped_column()  # JSON array as string
    video_url: Mapped[str | None] = mapped_column(default=None)  # YouTube/Vimeo embed URL

    # Publishing
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    is_featured: Mapped[bool] = mapped_column(default=False, index=True)
    is_bundle: Mapped[bool] = mapped_column(default=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    processes = relationship(
        "PackageProcess", back_populates="package", cascade="all, delete-orphan"
    )
    bundle_items = relationship(
        "PackageBundleItem",
        foreign_keys="PackageBundleItem.bundle_id",
        back_populates="bundle",
        cascade="all, delete-orphan",
    )
    course_items = relationship(
        "BundleCourseItem",
        foreign_keys="BundleCourseItem.bundle_id",
        back_populates="bundle",
        cascade="all, delete-orphan",
    )
    enrollments = relationship(
        "PackageEnrollment", back_populates="package", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Package(id={self.id}, slug={self.slug}, title={self.title})>"


class PackageProcess(Base):
    """Individual process/workflow included in a package"""

    __tablename__ = "package_processes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    sort_order: Mapped[int] = mapped_column(default=0)

    # Relationships
    package = relationship("Package", back_populates="processes")

    def __repr__(self) -> str:
        return f"<PackageProcess(id={self.id}, name={self.name}, package_id={self.package_id})>"


class PackageBundleItem(Base):
    """Bundle containing multiple packages"""

    __tablename__ = "package_bundle_items"
    __table_args__ = (
        UniqueConstraint("bundle_id", "child_package_id", name="uq_bundle_child_package"),
        Index("ix_bundle_items_bundle_child", "bundle_id", "child_package_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )  # Bundle package
    child_package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )  # Package within bundle
    sort_order: Mapped[int] = mapped_column(default=0)

    # Relationships
    bundle = relationship("Package", foreign_keys=[bundle_id], back_populates="bundle_items")
    child_package = relationship("Package", foreign_keys=[child_package_id])

    def __repr__(self) -> str:
        return (
            f"<PackageBundleItem(id={self.id}, "
            f"bundle_id={self.bundle_id}, "
            f"child_package_id={self.child_package_id})>"
        )
