"""Sales Window model for managing time-limited sales periods."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Enum, String

from app.db.session import Base


class SalesWindowStatus(str, enum.Enum):
    """Status enum for sales windows."""

    UPCOMING = "upcoming"
    ACTIVE = "active"
    CLOSED = "closed"


class SalesWindow(Base):
    """
    Sales Window model.

    Represents a time-limited period when course bundles are available for purchase.
    """

    __tablename__ = "sales_windows"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    status: Column[Any] = Column(
        Enum(SalesWindowStatus, name="sales_window_status"),
        nullable=False,
        default=SalesWindowStatus.UPCOMING,
        index=True,
    )
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Landing page configuration stored as JSON
    # Example: {"slug": "zimowe-2026", "title": "...", "subtitle": "...", "hero": {...}}
    landing_page_config = Column(JSON, nullable=False)

    # Early bird configuration (optional)
    # Example: {"enabled": false, "endsAt": "...", "discountPercentage": 10}
    early_bird_config = Column(JSON, nullable=True)

    # Bundle IDs associated with this sales window
    # Example: ["bundle-1", "bundle-2", "bundle-3"]
    bundle_ids = Column(JSON, nullable=False)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    created_by = Column(String(100), nullable=True)  # User ID who created
    updated_by = Column(String(100), nullable=True)  # User ID who last updated

    def __repr__(self) -> str:
        """String representation."""
        return f"<SalesWindow(id={self.id}, name={self.name}, status={self.status})>"
