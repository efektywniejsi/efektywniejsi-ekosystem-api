import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()

    role: Mapped[str] = mapped_column(default="paid")
    is_active: Mapped[bool] = mapped_column(default=True)

    password_reset_token: Mapped[str | None] = mapped_column(default=None, index=True)
    password_reset_token_expires: Mapped[datetime | None] = mapped_column(default=None)

    avatar_url: Mapped[str | None] = mapped_column(default=None)
    password_changed_at: Mapped[datetime | None] = mapped_column(default=None)
    totp_secret: Mapped[str | None] = mapped_column(default=None)
    totp_enabled: Mapped[bool] = mapped_column(default=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(default=None, index=True)
    notification_preferences: Mapped[dict | None] = mapped_column(type_=JSON, default=None)

    # Company / invoice data
    buyer_tax_no: Mapped[str | None] = mapped_column(default=None)
    buyer_company_name: Mapped[str | None] = mapped_column(default=None)
    buyer_street: Mapped[str | None] = mapped_column(default=None)
    buyer_post_code: Mapped[str | None] = mapped_column(default=None)
    buyer_city: Mapped[str | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships (explicit back_populates instead of implicit backref)
    enrollments = relationship("Enrollment", back_populates="user")
    lesson_progress = relationship("LessonProgress", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    streak = relationship("UserStreak", back_populates="user", uselist=False)
    points = relationship("UserPoints", back_populates="user", uselist=False)
    points_history = relationship("PointsHistory", back_populates="user")
    certificates = relationship("Certificate", back_populates="user")
    orders = relationship("Order", back_populates="user")
    package_enrollments = relationship("PackageEnrollment", back_populates="user")
    implementation_package_enrollments = relationship(
        "ImplementationPackageEnrollment", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
