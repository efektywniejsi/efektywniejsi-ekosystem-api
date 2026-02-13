import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class IntegrationProposal(Base):
    __tablename__ = "integration_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column()
    category: Mapped[str | None] = mapped_column(default=None)
    description: Mapped[str] = mapped_column(Text)
    official_docs_url: Mapped[str | None] = mapped_column(default=None)
    submitted_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Status: pending, approved, rejected
    status: Mapped[str] = mapped_column(default="pending", index=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    submitted_by = relationship("User")

    def __repr__(self) -> str:
        return f"<IntegrationProposal(id={self.id}, name={self.name}, status={self.status})>"
