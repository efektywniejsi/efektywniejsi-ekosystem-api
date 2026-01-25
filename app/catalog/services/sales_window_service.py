from datetime import datetime

from sqlalchemy.orm import Session

from app.catalog.models import SalesWindow
from app.catalog.schemas import SalesWindowStatus


class SalesWindowService:
    """Service layer for sales window business logic"""

    @staticmethod
    def get_active_sales_window(db: Session) -> SalesWindow | None:
        """Get currently active sales window"""
        now = datetime.utcnow()
        return (  # type: ignore[no-any-return]
            db.query(SalesWindow)
            .filter(
                SalesWindow.status == SalesWindowStatus.ACTIVE,
                SalesWindow.starts_at <= now,
                SalesWindow.ends_at >= now,
            )
            .first()
        )

    @staticmethod
    def get_all_sales_windows(db: Session) -> list[SalesWindow]:
        """Get all sales windows"""
        return db.query(SalesWindow).all()  # type: ignore[no-any-return]

    @staticmethod
    def get_sales_window_by_id(db: Session, window_id: str) -> SalesWindow | None:
        """Get sales window by ID"""
        return db.query(SalesWindow).filter(SalesWindow.id == window_id).first()  # type: ignore[no-any-return]
