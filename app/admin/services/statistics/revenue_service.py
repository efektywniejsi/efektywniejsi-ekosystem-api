"""Revenue statistics service."""

from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    Granularity,
    RevenueDataPoint,
    RevenueStatisticsResponse,
    RevenueSummary,
)
from app.admin.services.statistics.base import calculate_change_percent, get_previous_period
from app.packages.models.order import Order, OrderStatus


class RevenueService:
    """Service for revenue-related statistics."""

    @staticmethod
    def get_revenue_for_period(db: Session, start: datetime, end: datetime) -> tuple[int, int]:
        """Get total revenue and order count for a period.

        Uses payment_completed_at if available, otherwise falls back to created_at.

        Args:
            db: Database session.
            start: Period start datetime.
            end: Period end datetime.

        Returns:
            Tuple of (total_revenue, order_count).
        """
        result = (
            db.query(func.sum(Order.total), func.count(Order.id))
            .filter(
                Order.status == OrderStatus.COMPLETED,
                or_(
                    # Has payment_completed_at in range
                    (Order.payment_completed_at >= start) & (Order.payment_completed_at <= end),
                    # Or payment_completed_at is NULL but created_at is in range
                    (Order.payment_completed_at.is_(None))
                    & (Order.created_at >= start)
                    & (Order.created_at <= end),
                ),
            )
            .first()
        )
        if result is None:
            return 0, 0
        return result[0] or 0, result[1] or 0

    @staticmethod
    def get_statistics(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        granularity: Granularity = Granularity.DAILY,
        compare_previous: bool = True,
    ) -> RevenueStatisticsResponse:
        """Get detailed revenue statistics with chart data.

        Args:
            db: Database session.
            start_date: Period start.
            end_date: Period end.
            granularity: Data point granularity (daily, weekly, monthly).
            compare_previous: Whether to include previous period comparison.

        Returns:
            RevenueStatisticsResponse with current/previous summaries and data points.
        """
        current_revenue, current_count = RevenueService.get_revenue_for_period(
            db, start_date, end_date
        )
        avg_order_value = current_revenue // current_count if current_count > 0 else 0

        current_summary = RevenueSummary(
            total=current_revenue,
            orders_count=current_count,
            average_order_value=avg_order_value,
        )

        previous_summary = None
        change_percent = None
        if compare_previous:
            prev_start, prev_end = get_previous_period(start_date, end_date)
            prev_revenue, prev_count = RevenueService.get_revenue_for_period(
                db, prev_start, prev_end
            )
            prev_avg = prev_revenue // prev_count if prev_count > 0 else 0
            previous_summary = RevenueSummary(
                total=prev_revenue,
                orders_count=prev_count,
                average_order_value=prev_avg,
            )
            change_percent = calculate_change_percent(current_revenue, prev_revenue)

        data_points = RevenueService._get_data_points(db, start_date, end_date, granularity)

        return RevenueStatisticsResponse(
            current_period=current_summary,
            previous_period=previous_summary,
            change_percent=change_percent,
            data_points=data_points,
        )

    @staticmethod
    def _get_data_points(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        granularity: Granularity,
    ) -> list[RevenueDataPoint]:
        """Generate revenue data points for chart."""
        data_points = []

        if granularity == Granularity.DAILY:
            current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            while current <= end_date:
                next_day = current + timedelta(days=1)
                revenue, count = RevenueService.get_revenue_for_period(db, current, next_day)
                data_points.append(
                    RevenueDataPoint(
                        date=current.strftime("%Y-%m-%d"),
                        revenue=revenue,
                        orders_count=count,
                    )
                )
                current = next_day

        elif granularity == Granularity.WEEKLY:
            current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            week_num = 1
            while current <= end_date:
                next_week = current + timedelta(days=7)
                revenue, count = RevenueService.get_revenue_for_period(
                    db, current, min(next_week, end_date)
                )
                data_points.append(
                    RevenueDataPoint(
                        date=f"Week {week_num}",
                        revenue=revenue,
                        orders_count=count,
                    )
                )
                current = next_week
                week_num += 1

        elif granularity == Granularity.MONTHLY:
            current = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            while current <= end_date:
                if current.month == 12:
                    next_month = current.replace(year=current.year + 1, month=1)
                else:
                    next_month = current.replace(month=current.month + 1)
                revenue, count = RevenueService.get_revenue_for_period(
                    db, current, min(next_month, end_date)
                )
                data_points.append(
                    RevenueDataPoint(
                        date=current.strftime("%Y-%m"),
                        revenue=revenue,
                        orders_count=count,
                    )
                )
                current = next_month

        return data_points
