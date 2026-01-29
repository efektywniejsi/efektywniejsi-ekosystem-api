"""Statistics routes for admin dashboard."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    CertificatesListResponse,
    CompletionsListResponse,
    DailyUserDetailsResponse,
    DashboardSummaryResponse,
    EducationStatisticsResponse,
    Granularity,
    MonthlyUsersResponse,
    OrderDetailsListResponse,
    OrderStatisticsResponse,
    RankingsResponse,
    RevenueStatisticsResponse,
    SalesWindowsResponse,
    UserStatisticsResponse,
)
from app.admin.services.statistics_service import StatisticsService
from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/statistics", tags=["admin-statistics"])


@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DashboardSummaryResponse:
    """
    Get dashboard summary with all KPIs.

    Returns aggregated metrics for:
    - Revenue (today, week, month with change percentages)
    - Orders (today, pending, completed/failed this month)
    - Users (total, new, active)
    - Education (enrollments, completions, certificates)
    - Top 5 packages and courses
    """
    return StatisticsService.get_dashboard_summary(db)


@router.get("/revenue", response_model=RevenueStatisticsResponse)
async def get_revenue_statistics(
    start_date: datetime = Query(..., description="Start date for the period (ISO format)"),
    end_date: datetime = Query(..., description="End date for the period (ISO format)"),
    granularity: Granularity = Query(Granularity.DAILY, description="Data point granularity"),
    compare_previous: bool = Query(True, description="Include comparison with previous period"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> RevenueStatisticsResponse:
    """
    Get detailed revenue statistics.

    Returns:
    - Current period summary (total, order count, average order value)
    - Previous period summary for comparison
    - Change percentage
    - Data points for chart visualization
    """
    return StatisticsService.get_revenue_statistics(
        db, start_date, end_date, granularity, compare_previous
    )


@router.get("/orders", response_model=OrderStatisticsResponse)
async def get_order_statistics(
    start_date: datetime | None = Query(None, description="Filter start date"),
    end_date: datetime | None = Query(None, description="Filter end date"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> OrderStatisticsResponse:
    """
    Get order statistics with breakdowns.

    Returns:
    - Total orders count
    - Orders by status (pending, completed, failed, etc.)
    - Orders by payment provider (Stripe, PayU)
    - Recent 10 orders summary
    """
    return StatisticsService.get_order_statistics(db, start_date, end_date)


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    limit: int = Query(10, ge=1, le=50, description="Number of items per ranking"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> RankingsResponse:
    """
    Get rankings for packages and courses.

    Returns:
    - Top packages by sales count and revenue
    - Top courses by enrollment count and completion rate
    """
    return StatisticsService.get_rankings(db, limit)


@router.get("/sales-windows", response_model=SalesWindowsResponse)
async def get_sales_windows_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SalesWindowsResponse:
    """
    Get statistics for all sales windows.

    Returns metrics for each sales window:
    - Total orders during window
    - Total revenue
    - Unique customers
    """
    return StatisticsService.get_sales_windows_stats(db)


@router.get("/users", response_model=UserStatisticsResponse)
async def get_user_statistics(
    days: int = Query(30, ge=7, le=365, description="Number of days for activity trend"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserStatisticsResponse:
    """
    Get user statistics with activity trends.

    Returns:
    - Total users
    - Active users (today, week, month)
    - New users (today, week, month)
    - DAU/MAU ratio
    - Daily activity data points
    """
    return StatisticsService.get_user_statistics(db, days)


@router.get("/education", response_model=EducationStatisticsResponse)
async def get_education_statistics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> EducationStatisticsResponse:
    """
    Get education statistics.

    Returns:
    - Total enrollments
    - Active learners (last 7 days)
    - Course completions
    - Certificates issued
    - Per-course statistics with progress metrics
    """
    return StatisticsService.get_education_statistics(db)


@router.get("/orders/details", response_model=OrderDetailsListResponse)
async def get_order_details(
    period: str | None = Query(
        None, description="Period: 'today', 'this_month', or omit for all time"
    ),
    status: str | None = Query(None, description="Filter by status (e.g. 'completed', 'pending')"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of orders to return"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> OrderDetailsListResponse:
    """
    Get detailed order list with items for the KPI modal.

    Returns:
    - List of orders with their items
    - Total count
    - Total revenue (completed orders only)
    """
    return StatisticsService.get_order_details(db, period, status, limit)


@router.get("/users/monthly", response_model=MonthlyUsersResponse)
async def get_monthly_new_users(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MonthlyUsersResponse:
    """
    Get new users registered in the current month.

    Returns:
    - Total count
    - List of users with their details
    """
    return StatisticsService.get_monthly_new_users(db, limit)


@router.get("/education/completions", response_model=CompletionsListResponse)
async def get_completions(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of completions to return"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> CompletionsListResponse:
    """
    Get all course completions (most recent first).

    Returns:
    - Total count
    - List of completions with user and course details
    """
    return StatisticsService.get_completions(db, limit)


@router.get("/education/certificates", response_model=CertificatesListResponse)
async def get_certificates(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of certificates to return"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> CertificatesListResponse:
    """
    Get all issued certificates (most recent first).

    Returns:
    - Total count
    - List of certificates with user and course details
    """
    return StatisticsService.get_certificates(db, limit)


@router.get("/users/daily-details", response_model=DailyUserDetailsResponse)
async def get_daily_user_details(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    user_type: str = Query(..., alias="type", description="User type: 'active' or 'new'"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DailyUserDetailsResponse:
    """
    Get details of active or new users for a specific day.

    Returns:
    - Date
    - Type (active or new)
    - Total count
    - List of users with their details
    """
    return StatisticsService.get_daily_user_details(db, date, user_type, limit)
