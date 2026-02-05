"""Statistics module for aggregating data from various models.

This module is split into domain-specific services for better maintainability:
- base: Period helpers, calculation utilities
- dashboard_service: Dashboard summary KPIs
- revenue_service: Revenue statistics and data points
- order_service: Order statistics and breakdowns
- user_service: User statistics and activity
- education_service: Education stats, completions, certificates
- rankings_service: Package and course rankings
"""

from app.admin.services.statistics.base import (
    calculate_change_percent,
    count_active_users,
    get_period_boundaries,
    get_previous_period,
)
from app.admin.services.statistics.dashboard_service import DashboardService
from app.admin.services.statistics.education_service import EducationService
from app.admin.services.statistics.order_service import OrderStatisticsService
from app.admin.services.statistics.rankings_service import RankingsService
from app.admin.services.statistics.revenue_service import RevenueService
from app.admin.services.statistics.user_service import UserStatisticsService

__all__ = [
    # Base utilities
    "get_period_boundaries",
    "get_previous_period",
    "calculate_change_percent",
    "count_active_users",
    # Services
    "DashboardService",
    "RevenueService",
    "OrderStatisticsService",
    "RankingsService",
    "UserStatisticsService",
    "EducationService",
]
