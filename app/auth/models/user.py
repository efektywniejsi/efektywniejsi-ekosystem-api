import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

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

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
