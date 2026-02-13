import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.integrations.models.integration import Integration
    from app.packages.models.package import PackageProcess


class ProcessIntegration(Base):
    """Association between package processes and integrations"""

    __tablename__ = "process_integrations"
    __table_args__ = (
        UniqueConstraint("process_id", "integration_id", name="uq_process_integration"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("package_processes.id", ondelete="CASCADE"), index=True
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), index=True
    )
    context_note: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    integration: Mapped["Integration"] = relationship(
        "Integration", back_populates="process_integrations"
    )
    process: Mapped["PackageProcess"] = relationship(
        "PackageProcess", back_populates="integrations"
    )

    def __repr__(self) -> str:
        return f"<ProcessIntegration(process={self.process_id}, integration={self.integration_id})>"
