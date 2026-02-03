"""Statistics schemas for admin dashboard."""

from enum import Enum

from pydantic import BaseModel, Field

from app.core.datetime_utils import UTCDatetime


class Granularity(str, Enum):
    """Data point granularity for charts."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ============ KPI Models ============


class RevenueKPI(BaseModel):
    """Revenue key performance indicators."""

    today: int = Field(description="Today's revenue in grosz")
    this_week: int = Field(description="This week's revenue in grosz")
    this_month: int = Field(description="This month's revenue in grosz")
    change_percent_week: float = Field(description="Week over week change percentage")
    change_percent_month: float = Field(description="Month over month change percentage")


class OrdersKPI(BaseModel):
    """Orders key performance indicators."""

    today: int = Field(description="Orders placed today")
    pending: int = Field(description="Total pending orders")
    completed_this_month: int = Field(description="Completed orders this month")
    failed_this_month: int = Field(description="Failed orders this month")


class UsersKPI(BaseModel):
    """Users key performance indicators."""

    total: int = Field(description="Total registered users")
    new_this_month: int = Field(description="New users this month")
    active_today: int = Field(description="Users active today (accessed course)")
    active_this_week: int = Field(description="Users active this week")


class EducationKPI(BaseModel):
    """Education key performance indicators."""

    total_enrollments: int = Field(description="Total course enrollments")
    enrollments_this_month: int = Field(description="New enrollments this month")
    completions_this_month: int = Field(description="Course completions this month")
    certificates_this_month: int = Field(description="Certificates issued this month")
    average_completion_rate: float = Field(description="Average completion rate percentage")


# ============ Ranked Items ============


class RankedItem(BaseModel):
    """Ranked item for top lists."""

    id: str
    title: str
    slug: str
    count: int = Field(description="Sales count or enrollment count")
    revenue: int = Field(default=0, description="Revenue in grosz")


# ============ Dashboard Summary ============


class DashboardSummaryResponse(BaseModel):
    """Complete dashboard summary with all KPIs."""

    revenue: RevenueKPI
    orders: OrdersKPI
    users: UsersKPI
    education: EducationKPI
    top_packages: list[RankedItem] = Field(description="Top 5 packages by sales")
    top_courses: list[RankedItem] = Field(description="Top 5 courses by enrollments")


# ============ Revenue Statistics ============


class RevenueDataPoint(BaseModel):
    """Single data point for revenue chart."""

    date: str = Field(description="Date label (e.g., '2026-01-15' or 'Week 3')")
    revenue: int = Field(description="Revenue in grosz")
    orders_count: int = Field(description="Number of orders")


class RevenueSummary(BaseModel):
    """Revenue summary for a period."""

    total: int = Field(description="Total revenue in grosz")
    orders_count: int = Field(description="Total number of orders")
    average_order_value: int = Field(description="Average order value in grosz")
    currency: str = Field(default="PLN")


class RevenueStatisticsResponse(BaseModel):
    """Revenue statistics with comparison and chart data."""

    current_period: RevenueSummary
    previous_period: RevenueSummary | None = None
    change_percent: float | None = None
    data_points: list[RevenueDataPoint] = Field(description="Data points for chart")


# ============ Order Statistics ============


class OrderStatusCount(BaseModel):
    """Count of orders by status."""

    status: str
    count: int
    percentage: float


class OrderProviderCount(BaseModel):
    """Count of orders by payment provider."""

    provider: str
    count: int
    percentage: float
    revenue: int = Field(description="Revenue in grosz")


class OrderStatisticsResponse(BaseModel):
    """Order statistics with breakdowns."""

    total_orders: int
    by_status: list[OrderStatusCount]
    by_provider: list[OrderProviderCount]
    recent_orders: list[dict] = Field(description="Last 10 orders summary")


# ============ Rankings ============


class PackageRanking(BaseModel):
    """Package ranking by sales."""

    id: str
    title: str
    slug: str
    category: str
    sales_count: int
    total_revenue: int = Field(description="Revenue in grosz")
    is_bundle: bool


class CourseRanking(BaseModel):
    """Course ranking by enrollments."""

    id: str
    title: str
    slug: str
    category: str | None
    enrollment_count: int
    completion_count: int
    completion_rate: float


class RankingsResponse(BaseModel):
    """Rankings response with packages and courses."""

    packages: list[PackageRanking]
    courses: list[CourseRanking]


# ============ Sales Windows ============


class SalesWindowStats(BaseModel):
    """Statistics for a sales window."""

    id: str
    name: str
    status: str
    starts_at: UTCDatetime
    ends_at: UTCDatetime
    total_orders: int
    total_revenue: int = Field(description="Revenue in grosz")
    unique_customers: int
    conversion_rate: float | None = None


class SalesWindowsResponse(BaseModel):
    """Sales windows comparison response."""

    windows: list[SalesWindowStats]


# ============ User Statistics ============


class UserActivityDataPoint(BaseModel):
    """User activity data point for chart."""

    date: str
    active_users: int
    new_users: int


class UserStatisticsResponse(BaseModel):
    """User statistics response."""

    total_users: int
    active_users_today: int
    active_users_week: int
    active_users_month: int
    new_users_today: int
    new_users_week: int
    new_users_month: int
    dau_mau_ratio: float = Field(description="Daily/Monthly active users ratio")
    activity_data_points: list[UserActivityDataPoint]


# ============ Education Statistics ============


class CourseProgressStats(BaseModel):
    """Progress statistics for a course."""

    id: str
    title: str
    slug: str
    total_enrollments: int
    active_learners: int = Field(description="Users who accessed in last 7 days")
    completed_count: int
    average_progress: float = Field(description="Average completion percentage")
    certificates_issued: int


class EducationStatisticsResponse(BaseModel):
    """Education statistics response."""

    total_enrollments: int
    active_learners: int
    total_completions: int
    total_certificates: int
    average_completion_rate: float
    courses: list[CourseProgressStats]


# ============ Daily User Details ============


class UserDetail(BaseModel):
    """User detail for daily user list."""

    id: str
    email: str
    full_name: str | None
    created_at: UTCDatetime
    last_activity: UTCDatetime | None


class DailyUserDetailsResponse(BaseModel):
    """Response for daily user details endpoint."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    type: str = Field(description="Type: 'active' or 'new'")
    total: int = Field(description="Total count of users")
    users: list[UserDetail] = Field(description="List of users")


# ============ Order Details (Modal) ============


class OrderDetailItem(BaseModel):
    """Single item within an order."""

    package_title: str
    price: int = Field(description="Price in grosz")


class OrderDetailResponse(BaseModel):
    """Detailed order for the modal view."""

    id: str
    order_number: str
    email: str
    name: str
    status: str
    total: int = Field(description="Total in grosz")
    created_at: UTCDatetime
    items: list[OrderDetailItem]


class OrderDetailsListResponse(BaseModel):
    """Response for order details list endpoint."""

    orders: list[OrderDetailResponse]
    total_count: int
    total_revenue: int = Field(description="Total revenue in grosz")


# ============ Monthly Users (Modal) ============


class MonthlyUsersResponse(BaseModel):
    """Response for monthly new users endpoint."""

    total: int
    users: list[UserDetail]


# ============ Completions & Certificates (Modal) ============


class CompletionDetail(BaseModel):
    """Single course completion entry."""

    user_email: str
    user_name: str | None
    course_title: str
    completed_at: UTCDatetime


class CompletionsListResponse(BaseModel):
    """Response for monthly completions endpoint."""

    total: int
    completions: list[CompletionDetail]


class CertificateDetail(BaseModel):
    """Single certificate entry."""

    user_email: str
    user_name: str | None
    course_title: str
    certificate_code: str
    issued_at: UTCDatetime


class CertificatesListResponse(BaseModel):
    """Response for monthly certificates endpoint."""

    total: int
    certificates: list[CertificateDetail]
