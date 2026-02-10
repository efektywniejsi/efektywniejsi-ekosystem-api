import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.integrations.models.integration import Integration


class IntegrationType(Base):
    __tablename__ = "integration_types"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), index=True
    )
    type_name: Mapped[str] = mapped_column()  # "API", "OAuth 2.0", "MCP"

    integration: Mapped["Integration"] = relationship(
        "Integration", back_populates="integration_types"
    )

    def __repr__(self) -> str:
        return f"<IntegrationType(id={self.id}, type_name={self.type_name})>"
