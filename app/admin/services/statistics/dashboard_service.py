"""Dashboard statistics service."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import DashboardSummaryResponse, RevenueKPI
from app.admin.services.statistics.base import calculate_change_percent
from app.admin.services.statistics.education_service import EducationService
from app.admin.services.statistics.order_service import OrderStatisticsService
from app.admin.services.statistics.rankings_service import RankingsService
from app.admin.services.statistics.revenue_service import RevenueService
from app.admin.services.statistics.user_service import UserStatisticsService


class DashboardService:
    """Service for dashboard summary aggregation."""

    @staticmethod
    def get_summary(db: Session) -> DashboardSummaryResponse:
        """Get complete dashboard summary with all KPIs.

        This method aggregates data from all specialized services to build
        a comprehensive dashboard view.

        Args:
            db: Database session.

        Returns:
            DashboardSummaryResponse with all KPIs and top items.
        """
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_week_start = week_start - timedelta(days=7)

        # Revenue KPIs
        today_revenue, _ = RevenueService.get_revenue_for_period(db, today_start, now)
        week_revenue, _ = RevenueService.get_revenue_for_period(db, week_start, now)
        month_revenue, _ = RevenueService.get_revenue_for_period(db, month_start, now)
        prev_week_revenue, _ = RevenueService.get_revenue_for_period(
            db, prev_week_start, week_start
        )
        prev_month_revenue, _ = RevenueService.get_revenue_for_period(
            db, prev_month_start, month_start
        )

        revenue_kpi = RevenueKPI(
            today=today_revenue,
            this_week=week_revenue,
            this_month=month_revenue,
            change_percent_week=calculate_change_percent(week_revenue, prev_week_revenue),
            change_percent_month=calculate_change_percent(month_revenue, prev_month_revenue),
        )

        # Other KPIs from specialized services
        orders_kpi = OrderStatisticsService.get_kpis(db, today_start, month_start)
        users_kpi = UserStatisticsService.get_kpis(db, today_start, week_start, month_start)
        education_kpi = EducationService.get_kpis(db, month_start)

        # Top items from rankings service
        top_packages = RankingsService.get_top_packages(db, limit=5)
        top_courses = RankingsService.get_top_courses(db, limit=5)

        return DashboardSummaryResponse(
            revenue=revenue_kpi,
            orders=orders_kpi,
            users=users_kpi,
            education=education_kpi,
            top_packages=top_packages,
            top_courses=top_courses,
        )
