"""Statistics service for aggregating data from various models."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    CertificateDetail,
    CertificatesListResponse,
    CompletionDetail,
    CompletionsListResponse,
    CourseProgressStats,
    CourseRanking,
    DailyUserDetailsResponse,
    DashboardSummaryResponse,
    EducationKPI,
    EducationStatisticsResponse,
    Granularity,
    MonthlyUsersResponse,
    OrderDetailItem,
    OrderDetailResponse,
    OrderDetailsListResponse,
    OrderProviderCount,
    OrdersKPI,
    OrderStatisticsResponse,
    OrderStatusCount,
    PackageRanking,
    RankedItem,
    RankingsResponse,
    RevenueDataPoint,
    RevenueKPI,
    RevenueStatisticsResponse,
    RevenueSummary,
    SalesWindowsResponse,
    SalesWindowStats,
    UserActivityDataPoint,
    UserDetail,
    UsersKPI,
    UserStatisticsResponse,
)
from app.auth.models.user import User
from app.auth.models.user_daily_activity import UserDailyActivity
from app.courses.models.certificate import Certificate
from app.courses.models.course import Course
from app.courses.models.enrollment import Enrollment
from app.courses.models.progress import LessonProgress
from app.packages.models.order import Order, OrderItem, OrderStatus
from app.packages.models.package import Package
from app.packages.models.sales_window import SalesWindow


class StatisticsService:
    """Service for calculating and aggregating statistics."""

    # ============ Helper Methods ============

    @staticmethod
    def _get_period_boundaries(period: str) -> tuple[datetime, datetime]:
        """Get start and end datetime for a period."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "today":
            return today_start, now
        elif period == "this_week":
            week_start = today_start - timedelta(days=today_start.weekday())
            return week_start, now
        elif period == "this_month":
            month_start = today_start.replace(day=1)
            return month_start, now
        elif period == "last_30_days":
            return today_start - timedelta(days=30), now
        elif period == "last_90_days":
            return today_start - timedelta(days=90), now
        elif period == "this_year":
            year_start = today_start.replace(month=1, day=1)
            return year_start, now
        else:
            return today_start - timedelta(days=30), now

    @staticmethod
    def _get_previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
        """Get the previous period of the same duration."""
        duration = end - start
        return start - duration, start

    @staticmethod
    def _calculate_change_percent(current: int | float, previous: int | float) -> float:
        """Calculate percentage change between two values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    @staticmethod
    def _count_active_users(
        db: Session,
        since: datetime,
        until: datetime | None = None,
    ) -> int:
        """Count distinct active users from daily activity log."""
        query = db.query(func.count(func.distinct(UserDailyActivity.user_id))).filter(
            UserDailyActivity.date >= since.date()
        )
        if until is not None:
            query = query.filter(UserDailyActivity.date < until.date())
        return query.scalar() or 0

    # ============ Revenue Methods ============

    @staticmethod
    def get_revenue_for_period(db: Session, start: datetime, end: datetime) -> tuple[int, int]:
        """Get total revenue and order count for a period."""
        # Use payment_completed_at if available, otherwise fall back to created_at
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

    # ============ Dashboard Summary ============

    @staticmethod
    def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
        """Get complete dashboard summary with all KPIs."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_week_start = week_start - timedelta(days=7)

        # Revenue KPIs
        today_revenue, _ = StatisticsService.get_revenue_for_period(db, today_start, now)
        week_revenue, _ = StatisticsService.get_revenue_for_period(db, week_start, now)
        month_revenue, _ = StatisticsService.get_revenue_for_period(db, month_start, now)
        prev_week_revenue, _ = StatisticsService.get_revenue_for_period(
            db, prev_week_start, week_start
        )
        prev_month_revenue, _ = StatisticsService.get_revenue_for_period(
            db, prev_month_start, month_start
        )

        revenue_kpi = RevenueKPI(
            today=today_revenue,
            this_week=week_revenue,
            this_month=month_revenue,
            change_percent_week=StatisticsService._calculate_change_percent(
                week_revenue, prev_week_revenue
            ),
            change_percent_month=StatisticsService._calculate_change_percent(
                month_revenue, prev_month_revenue
            ),
        )

        # Orders KPIs
        today_orders = db.query(Order).filter(Order.created_at >= today_start).count()
        pending_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING).count()
        completed_month = (
            db.query(Order)
            .filter(
                Order.status == OrderStatus.COMPLETED,
                Order.payment_completed_at >= month_start,
            )
            .count()
        )
        failed_month = (
            db.query(Order)
            .filter(Order.status == OrderStatus.FAILED, Order.created_at >= month_start)
            .count()
        )

        orders_kpi = OrdersKPI(
            today=today_orders,
            pending=pending_orders,
            completed_this_month=completed_month,
            failed_this_month=failed_month,
        )

        # Users KPIs
        total_users = db.query(User).filter(User.is_active.is_(True)).count()
        new_users_month = db.query(User).filter(User.created_at >= month_start).count()

        # Active users based on course access OR daily activity log
        active_today = StatisticsService._count_active_users(db, today_start)
        active_week = StatisticsService._count_active_users(db, week_start)

        users_kpi = UsersKPI(
            total=total_users,
            new_this_month=new_users_month,
            active_today=active_today,
            active_this_week=active_week,
        )

        # Education KPIs
        total_enrollments = db.query(Enrollment).count()
        enrollments_month = (
            db.query(Enrollment).filter(Enrollment.enrolled_at >= month_start).count()
        )
        completions_month = (
            db.query(Enrollment)
            .filter(
                Enrollment.completed_at.isnot(None),
                Enrollment.completed_at >= month_start,
            )
            .count()
        )
        certificates_month = (
            db.query(Certificate).filter(Certificate.issued_at >= month_start).count()
        )

        # Average completion rate
        total_completed = db.query(Enrollment).filter(Enrollment.completed_at.isnot(None)).count()
        avg_completion = (
            round((total_completed / total_enrollments) * 100, 2) if total_enrollments > 0 else 0.0
        )

        education_kpi = EducationKPI(
            total_enrollments=total_enrollments,
            enrollments_this_month=enrollments_month,
            completions_this_month=completions_month,
            certificates_this_month=certificates_month,
            average_completion_rate=avg_completion,
        )

        # Top Packages by sales
        top_packages_query = (
            db.query(
                Package.id,
                Package.title,
                Package.slug,
                func.count(OrderItem.id).label("count"),
                func.sum(OrderItem.price).label("revenue"),
            )
            .join(OrderItem, OrderItem.package_id == Package.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status == OrderStatus.COMPLETED)
            .group_by(Package.id)
            .order_by(func.count(OrderItem.id).desc())
            .limit(5)
            .all()
        )

        top_packages = [
            RankedItem(
                id=str(p.id), title=p.title, slug=p.slug, count=p.count, revenue=p.revenue or 0
            )
            for p in top_packages_query
        ]

        # Top Courses by enrollments
        top_courses_query = (
            db.query(
                Course.id,
                Course.title,
                Course.slug,
                func.count(Enrollment.id).label("count"),
            )
            .join(Enrollment, Enrollment.course_id == Course.id)
            .group_by(Course.id)
            .order_by(func.count(Enrollment.id).desc())
            .limit(5)
            .all()
        )

        top_courses = [
            RankedItem(id=str(c.id), title=c.title, slug=c.slug, count=c.count, revenue=0)
            for c in top_courses_query
        ]

        return DashboardSummaryResponse(
            revenue=revenue_kpi,
            orders=orders_kpi,
            users=users_kpi,
            education=education_kpi,
            top_packages=top_packages,
            top_courses=top_courses,
        )

    # ============ Revenue Statistics ============

    @staticmethod
    def get_revenue_statistics(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        granularity: Granularity = Granularity.DAILY,
        compare_previous: bool = True,
    ) -> RevenueStatisticsResponse:
        """Get detailed revenue statistics with chart data."""
        # Current period
        current_revenue, current_count = StatisticsService.get_revenue_for_period(
            db, start_date, end_date
        )
        avg_order_value = current_revenue // current_count if current_count > 0 else 0

        current_summary = RevenueSummary(
            total=current_revenue,
            orders_count=current_count,
            average_order_value=avg_order_value,
        )

        # Previous period
        previous_summary = None
        change_percent = None
        if compare_previous:
            prev_start, prev_end = StatisticsService._get_previous_period(start_date, end_date)
            prev_revenue, prev_count = StatisticsService.get_revenue_for_period(
                db, prev_start, prev_end
            )
            prev_avg = prev_revenue // prev_count if prev_count > 0 else 0
            previous_summary = RevenueSummary(
                total=prev_revenue,
                orders_count=prev_count,
                average_order_value=prev_avg,
            )
            change_percent = StatisticsService._calculate_change_percent(
                current_revenue, prev_revenue
            )

        # Data points for chart
        data_points = StatisticsService._get_revenue_data_points(
            db, start_date, end_date, granularity
        )

        return RevenueStatisticsResponse(
            current_period=current_summary,
            previous_period=previous_summary,
            change_percent=change_percent,
            data_points=data_points,
        )

    @staticmethod
    def _get_revenue_data_points(
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
                revenue, count = StatisticsService.get_revenue_for_period(db, current, next_day)
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
                revenue, count = StatisticsService.get_revenue_for_period(
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
                revenue, count = StatisticsService.get_revenue_for_period(
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

    # ============ Order Statistics ============

    @staticmethod
    def get_order_statistics(
        db: Session, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> OrderStatisticsResponse:
        """Get order statistics with breakdowns."""
        query = db.query(Order)
        if start_date:
            query = query.filter(Order.created_at >= start_date)
        if end_date:
            query = query.filter(Order.created_at <= end_date)

        total_orders = query.count()

        # By status
        status_counts = (
            query.with_entities(Order.status, func.count(Order.id)).group_by(Order.status).all()
        )
        by_status = [
            OrderStatusCount(
                status=s.value if hasattr(s, "value") else str(s),
                count=c,
                percentage=round((c / total_orders) * 100, 2) if total_orders > 0 else 0,
            )
            for s, c in status_counts
        ]

        # By provider
        provider_stats = (
            query.filter(Order.status == OrderStatus.COMPLETED)
            .with_entities(
                Order.payment_provider,
                func.count(Order.id),
                func.sum(Order.total),
            )
            .group_by(Order.payment_provider)
            .all()
        )
        completed_total = sum(p[1] for p in provider_stats)
        by_provider = [
            OrderProviderCount(
                provider=p.value if hasattr(p, "value") else str(p),
                count=c,
                percentage=round((c / completed_total) * 100, 2) if completed_total > 0 else 0,
                revenue=r or 0,
            )
            for p, c, r in provider_stats
        ]

        # Recent orders
        recent = db.query(Order).order_by(Order.created_at.desc()).limit(10).all()
        recent_orders = [
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "email": o.email,
                "status": o.status.value,
                "total": o.total,
                "created_at": o.created_at.isoformat(),
            }
            for o in recent
        ]

        return OrderStatisticsResponse(
            total_orders=total_orders,
            by_status=by_status,
            by_provider=by_provider,
            recent_orders=recent_orders,
        )

    # ============ Rankings ============

    @staticmethod
    def get_rankings(db: Session, limit: int = 10) -> RankingsResponse:
        """Get rankings for packages and courses."""
        # Package rankings
        package_stats = (
            db.query(
                Package.id,
                Package.title,
                Package.slug,
                Package.category,
                Package.is_bundle,
                func.count(OrderItem.id).label("sales"),
                func.sum(OrderItem.price).label("revenue"),
            )
            .join(OrderItem, OrderItem.package_id == Package.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status == OrderStatus.COMPLETED)
            .group_by(Package.id)
            .order_by(func.count(OrderItem.id).desc())
            .limit(limit)
            .all()
        )

        packages = [
            PackageRanking(
                id=str(p.id),
                title=p.title,
                slug=p.slug,
                category=p.category,
                sales_count=p.sales,
                total_revenue=p.revenue or 0,
                is_bundle=p.is_bundle,
            )
            for p in package_stats
        ]

        # Course rankings
        course_stats = (
            db.query(
                Course.id,
                Course.title,
                Course.slug,
                Course.category,
                func.count(Enrollment.id).label("enrollments"),
            )
            .join(Enrollment, Enrollment.course_id == Course.id)
            .group_by(Course.id)
            .order_by(func.count(Enrollment.id).desc())
            .limit(limit)
            .all()
        )

        # Build course rankings with completion rates
        courses = []
        for c in course_stats:
            completion_count = (
                db.query(Enrollment)
                .filter(Enrollment.course_id == c.id, Enrollment.completed_at.isnot(None))
                .count()
            )
            completion_rate = (
                round((completion_count / c.enrollments) * 100, 2) if c.enrollments > 0 else 0.0
            )
            courses.append(
                CourseRanking(
                    id=str(c.id),
                    title=c.title,
                    slug=c.slug,
                    category=c.category,
                    enrollment_count=c.enrollments,
                    completion_count=completion_count,
                    completion_rate=completion_rate,
                )
            )

        return RankingsResponse(packages=packages, courses=courses)

    # ============ Sales Windows ============

    @staticmethod
    def get_sales_windows_stats(db: Session) -> SalesWindowsResponse:
        """Get statistics for sales windows."""
        windows = db.query(SalesWindow).order_by(SalesWindow.starts_at.desc()).all()

        window_stats = []
        for w in windows:
            # Get orders during window period
            orders_query = db.query(Order).filter(
                Order.status == OrderStatus.COMPLETED,
                Order.payment_completed_at >= w.starts_at,
                Order.payment_completed_at <= w.ends_at,
            )

            total_orders = orders_query.count()
            total_revenue = (
                db.query(func.sum(Order.total))
                .filter(
                    Order.status == OrderStatus.COMPLETED,
                    Order.payment_completed_at >= w.starts_at,
                    Order.payment_completed_at <= w.ends_at,
                )
                .scalar()
                or 0
            )
            unique_customers = (
                db.query(func.count(func.distinct(Order.email)))
                .filter(
                    Order.status == OrderStatus.COMPLETED,
                    Order.payment_completed_at >= w.starts_at,
                    Order.payment_completed_at <= w.ends_at,
                )
                .scalar()
                or 0
            )

            window_stats.append(
                SalesWindowStats(
                    id=str(w.id),
                    name=w.name,
                    status=w.status,
                    starts_at=w.starts_at,
                    ends_at=w.ends_at,
                    total_orders=total_orders,
                    total_revenue=total_revenue,
                    unique_customers=unique_customers,
                )
            )

        return SalesWindowsResponse(windows=window_stats)

    # ============ User Statistics ============

    @staticmethod
    def get_user_statistics(db: Session, days: int = 30) -> UserStatisticsResponse:
        """Get user statistics with activity trends."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        period_start = today_start - timedelta(days=days)

        total_users = db.query(User).filter(User.is_active.is_(True)).count()

        # Active users counts (course access OR login)
        active_today = StatisticsService._count_active_users(db, today_start)
        active_week = StatisticsService._count_active_users(db, week_start)
        active_month = StatisticsService._count_active_users(db, month_start)

        # New users counts
        new_today = db.query(User).filter(User.created_at >= today_start).count()
        new_week = db.query(User).filter(User.created_at >= week_start).count()
        new_month = db.query(User).filter(User.created_at >= month_start).count()

        # DAU/MAU ratio
        dau_mau = round(active_today / active_month, 4) if active_month > 0 else 0.0

        # Activity data points — single grouped query
        activity_rows = (
            db.query(
                UserDailyActivity.date,
                func.count(func.distinct(UserDailyActivity.user_id)),
            )
            .filter(
                UserDailyActivity.date >= period_start.date(),
                UserDailyActivity.date <= today_start.date(),
            )
            .group_by(UserDailyActivity.date)
            .all()
        )
        activity_by_day: dict[date, int] = {row[0]: row[1] for row in activity_rows}

        new_by_day_rows = (
            db.query(
                func.date(User.created_at).label("day"),
                func.count(User.id),
            )
            .filter(User.created_at >= period_start, User.created_at <= now)
            .group_by("day")
            .all()
        )
        new_by_day = {row[0]: row[1] for row in new_by_day_rows}

        data_points = []
        current = period_start
        while current <= today_start:
            d = current.date()
            data_points.append(
                UserActivityDataPoint(
                    date=current.strftime("%Y-%m-%d"),
                    active_users=activity_by_day.get(d, 0),
                    new_users=new_by_day.get(d, 0),
                )
            )
            current = current + timedelta(days=1)

        return UserStatisticsResponse(
            total_users=total_users,
            active_users_today=active_today,
            active_users_week=active_week,
            active_users_month=active_month,
            new_users_today=new_today,
            new_users_week=new_week,
            new_users_month=new_month,
            dau_mau_ratio=dau_mau,
            activity_data_points=data_points,
        )

    # ============ Education Statistics ============

    @staticmethod
    def get_education_statistics(db: Session) -> EducationStatisticsResponse:
        """Get education statistics with course details."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        total_enrollments = db.query(Enrollment).count()
        active_learners = (
            db.query(func.count(func.distinct(Enrollment.user_id)))
            .filter(Enrollment.last_accessed_at >= week_ago)
            .scalar()
            or 0
        )
        total_completions = db.query(Enrollment).filter(Enrollment.completed_at.isnot(None)).count()
        total_certificates = db.query(Certificate).count()
        avg_completion_rate = (
            round((total_completions / total_enrollments) * 100, 2)
            if total_enrollments > 0
            else 0.0
        )

        # Per-course statistics
        courses_data = db.query(Course).filter(Course.is_published.is_(True)).all()

        courses = []
        for course in courses_data:
            enrollments = db.query(Enrollment).filter(Enrollment.course_id == course.id).count()
            active = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course.id,
                    Enrollment.last_accessed_at >= week_ago,
                )
                .count()
            )
            completed = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course.id,
                    Enrollment.completed_at.isnot(None),
                )
                .count()
            )
            certs = db.query(Certificate).filter(Certificate.course_id == course.id).count()

            # Calculate average progress
            progress_data = (
                db.query(func.avg(LessonProgress.completion_percentage))
                .join(
                    Enrollment,
                    (Enrollment.user_id == LessonProgress.user_id)
                    & (Enrollment.course_id == course.id),
                )
                .scalar()
            )
            avg_progress = round(progress_data or 0, 2)

            courses.append(
                CourseProgressStats(
                    id=str(course.id),
                    title=course.title,
                    slug=course.slug,
                    total_enrollments=enrollments,
                    active_learners=active,
                    completed_count=completed,
                    average_progress=avg_progress,
                    certificates_issued=certs,
                )
            )

        return EducationStatisticsResponse(
            total_enrollments=total_enrollments,
            active_learners=active_learners,
            total_completions=total_completions,
            total_certificates=total_certificates,
            average_completion_rate=avg_completion_rate,
            courses=courses,
        )

    # ============ Daily User Details ============

    @staticmethod
    def get_daily_user_details(
        db: Session, date: str, user_type: str, limit: int = 50
    ) -> DailyUserDetailsResponse:
        """Get list of active or new users for a specific day."""
        from datetime import datetime

        # Parse the date
        target_date = datetime.strptime(date, "%Y-%m-%d")
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        users_list = []

        if user_type == "active":
            target_day = target_date.date()

            activities = (
                db.query(UserDailyActivity)
                .filter(UserDailyActivity.date == target_day)
                .limit(limit)
                .all()
            )
            user_ids = [a.user_id for a in activities]
            users_map = (
                {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
                if user_ids
                else {}
            )

            for activity in activities:
                user = users_map.get(activity.user_id)
                if user:
                    users_list.append(
                        UserDetail(
                            id=str(user.id),
                            email=user.email,
                            full_name=user.name,
                            created_at=user.created_at,
                            last_activity=activity.last_seen_at,
                        )
                    )

            total = (
                db.query(func.count(UserDailyActivity.id))
                .filter(UserDailyActivity.date == target_day)
                .scalar()
                or 0
            )

        elif user_type == "new":
            # Get users created on this day
            users = (
                db.query(User)
                .filter(
                    User.created_at >= day_start,
                    User.created_at < day_end,
                )
                .order_by(User.created_at.desc())
                .limit(limit)
                .all()
            )

            for user in users:
                # Get last activity from enrollments
                last_activity = (
                    db.query(func.max(Enrollment.last_accessed_at))
                    .filter(Enrollment.user_id == user.id)
                    .scalar()
                )
                users_list.append(
                    UserDetail(
                        id=str(user.id),
                        email=user.email,
                        full_name=user.name,
                        created_at=user.created_at,
                        last_activity=last_activity,
                    )
                )

            # Get total count
            total = (
                db.query(User)
                .filter(
                    User.created_at >= day_start,
                    User.created_at < day_end,
                )
                .count()
            )
        else:
            total = 0

        return DailyUserDetailsResponse(
            date=date,
            type=user_type,
            total=total,
            users=users_list,
        )

    # ============ Order Details (Modal) ============

    @staticmethod
    def get_order_details(
        db: Session,
        period: str | None = "this_month",
        status: str | None = None,
        limit: int = 50,
    ) -> OrderDetailsListResponse:
        """Get detailed order list with items for the modal view."""
        query = db.query(Order)

        if period:
            start, end = StatisticsService._get_period_boundaries(period)
            query = query.filter(
                Order.created_at >= start,
                Order.created_at <= end,
            )

        if status:
            query = query.filter(Order.status == status)

        total_count = query.count()

        # Total revenue (completed only within the same filters)
        revenue_query = db.query(func.sum(Order.total)).filter(
            Order.status == OrderStatus.COMPLETED,
        )
        if period:
            revenue_query = revenue_query.filter(
                Order.created_at >= start,
                Order.created_at <= end,
            )
        total_revenue = revenue_query.scalar() or 0

        orders = query.order_by(Order.created_at.desc()).limit(limit).all()

        order_responses = []
        for order in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            order_responses.append(
                OrderDetailResponse(
                    id=str(order.id),
                    order_number=order.order_number,
                    email=order.email,
                    name=order.name,
                    status=order.status.value
                    if hasattr(order.status, "value")
                    else str(order.status),
                    total=order.total,
                    created_at=order.created_at,
                    items=[
                        OrderDetailItem(package_title=item.package_title, price=item.price)
                        for item in items
                    ],
                )
            )

        return OrderDetailsListResponse(
            orders=order_responses,
            total_count=total_count,
            total_revenue=total_revenue,
        )

    # ============ Monthly Users (Modal) ============

    @staticmethod
    def get_monthly_new_users(db: Session, limit: int = 50) -> MonthlyUsersResponse:
        """Get new users registered in the current month."""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total = db.query(User).filter(User.created_at >= month_start).count()

        users = (
            db.query(User)
            .filter(User.created_at >= month_start)
            .order_by(User.created_at.desc())
            .limit(limit)
            .all()
        )

        user_ids = [u.id for u in users]
        last_activity_map = {}
        if user_ids:
            rows = (
                db.query(
                    UserDailyActivity.user_id,
                    func.max(UserDailyActivity.last_seen_at),
                )
                .filter(UserDailyActivity.user_id.in_(user_ids))
                .group_by(UserDailyActivity.user_id)
                .all()
            )
            last_activity_map = {r[0]: r[1] for r in rows}

        users_list = [
            UserDetail(
                id=str(user.id),
                email=user.email,
                full_name=user.name,
                created_at=user.created_at,
                last_activity=last_activity_map.get(user.id),
            )
            for user in users
        ]

        return MonthlyUsersResponse(total=total, users=users_list)

    # ============ Completions (Modal) ============

    @staticmethod
    def get_completions(db: Session, limit: int = 50) -> CompletionsListResponse:
        """Get all course completions (most recent first)."""
        total = db.query(Enrollment).filter(Enrollment.completed_at.isnot(None)).count()

        enrollments = (
            db.query(Enrollment)
            .filter(Enrollment.completed_at.isnot(None))
            .order_by(Enrollment.completed_at.desc())
            .limit(limit)
            .all()
        )

        completions = []
        for e in enrollments:
            user = db.query(User).filter(User.id == e.user_id).first()
            course = db.query(Course).filter(Course.id == e.course_id).first()
            completions.append(
                CompletionDetail(
                    user_email=user.email if user else "",
                    user_name=user.name if user else None,
                    course_title=course.title if course else "",
                    completed_at=e.completed_at,
                )
            )

        return CompletionsListResponse(total=total, completions=completions)

    # ============ Certificates (Modal) ============

    @staticmethod
    def get_certificates(db: Session, limit: int = 50) -> CertificatesListResponse:
        """Get all issued certificates (most recent first)."""
        total = db.query(Certificate).count()

        certs = db.query(Certificate).order_by(Certificate.issued_at.desc()).limit(limit).all()

        certificates = []
        for c in certs:
            user = db.query(User).filter(User.id == c.user_id).first()
            course = db.query(Course).filter(Course.id == c.course_id).first()
            certificates.append(
                CertificateDetail(
                    user_email=user.email if user else "",
                    user_name=user.name if user else None,
                    course_title=course.title if course else "",
                    certificate_code=c.certificate_code,
                    issued_at=c.issued_at,
                )
            )

        return CertificatesListResponse(total=total, certificates=certificates)
