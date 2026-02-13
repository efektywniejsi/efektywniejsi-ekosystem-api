"""Service layer for Sales Window operations."""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.packages.models import SalesWindow


class SalesWindowService:
    """Service for managing sales windows."""

    @staticmethod
    def get_all_sales_windows(db: Session) -> list[SalesWindow]:
        """
        Get all sales windows (admin only).

        Returns:
            List of all sales windows ordered by created_at descending
        """
        return cast(
            list[SalesWindow],
            db.query(SalesWindow).order_by(SalesWindow.created_at.desc()).all(),
        )

    @staticmethod
    def get_sales_window_by_id(db: Session, window_id: str) -> SalesWindow | None:
        """
        Get a single sales window by ID.

        Args:
            db: Database session
            window_id: Sales window ID (UUID as string)

        Returns:
            SalesWindow if found, None otherwise
        """
        return cast(
            SalesWindow | None,
            db.query(SalesWindow).filter(SalesWindow.id == window_id).first(),
        )

    @staticmethod
    def get_active_sales_window(db: Session) -> SalesWindow | None:
        """
        Get the currently active sales window.

        A sales window is active if:
        - status is 'active'
        - current time is between starts_at and ends_at

        Returns:
            Active SalesWindow if found, None otherwise
        """
        now = datetime.now(UTC)

        return cast(
            SalesWindow | None,
            db.query(SalesWindow)
            .filter(
                and_(
                    SalesWindow.status == "active",
                    SalesWindow.starts_at <= now,
                    SalesWindow.ends_at >= now,
                )
            )
            .order_by(SalesWindow.starts_at.desc())
            .first(),
        )

    @staticmethod
    def get_next_sales_window(db: Session) -> SalesWindow | None:
        """
        Get the next upcoming sales window.

        Returns:
            Upcoming SalesWindow if found, None otherwise
        """
        now = datetime.now(UTC)

        return cast(
            SalesWindow | None,
            db.query(SalesWindow)
            .filter(
                and_(
                    SalesWindow.status == "upcoming",
                    SalesWindow.starts_at > now,
                )
            )
            .order_by(SalesWindow.starts_at.asc())
            .first(),
        )
