"""Sales Window model for managing time-limited sales campaigns."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SalesWindowStatus(str, enum.Enum):
    """Sales window status enum."""

    UPCOMING = "upcoming"
    ACTIVE = "active"
    CLOSED = "closed"


class SalesWindow(Base):
    """
    Sales Window for time-limited promotions.

    Attributes:
        id: Unique identifier (UUID)
        name: Internal name for the sales window
        status: Current status (upcoming, active, closed)
        starts_at: When the sale starts
        ends_at: When the sale ends
        landing_page_config: JSON config for landing page (slug, title, hero, etc.)
        early_bird_config: JSON config for early bird pricing (optional)
        bundle_ids: List of bundle IDs to show in this sale
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User ID who created the window
        updated_by: User ID who last updated the window
    """

    __tablename__ = "sales_windows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            SalesWindowStatus,
            name="saleswindowstatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default="upcoming",
        index=True,
    )

    # Time range
    starts_at: Mapped[datetime] = mapped_column(index=True)
    ends_at: Mapped[datetime] = mapped_column(index=True)

    # Configuration (stored as JSONB)
    landing_page_config: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    early_bird_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Bundle IDs (stored as JSONB array)
    bundle_ids: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        # Index for finding active sales windows
        Index("idx_sales_window_active_time", "status", "starts_at", "ends_at"),
        # Index for admin queries
        Index("idx_sales_window_created", "created_at", "status"),
    )

    def __repr__(self) -> str:
        return f"<SalesWindow(id={self.id}, name={self.name}, status={self.status})>"
