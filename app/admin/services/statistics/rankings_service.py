"""Rankings statistics service."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    CourseRanking,
    PackageRanking,
    RankedItem,
    RankingsResponse,
    SalesWindowsResponse,
    SalesWindowStats,
)
from app.courses.models.course import Course
from app.courses.models.enrollment import Enrollment
from app.packages.models.order import Order, OrderItem, OrderStatus
from app.packages.models.package import Package
from app.packages.models.sales_window import SalesWindow


class RankingsService:
    """Service for rankings and sales window statistics."""

    @staticmethod
    def get_top_packages(db: Session, limit: int = 5) -> list[RankedItem]:
        """Get top packages by sales count.

        Args:
            db: Database session.
            limit: Maximum number of packages to return.

        Returns:
            List of RankedItem with package details and sales metrics.
        """
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
            .limit(limit)
            .all()
        )

        return [
            RankedItem(
                id=str(p.id), title=p.title, slug=p.slug, count=p.count, revenue=p.revenue or 0
            )
            for p in top_packages_query
        ]

    @staticmethod
    def get_top_courses(db: Session, limit: int = 5) -> list[RankedItem]:
        """Get top courses by enrollment count.

        Args:
            db: Database session.
            limit: Maximum number of courses to return.

        Returns:
            List of RankedItem with course details and enrollment count.
        """
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
            .limit(limit)
            .all()
        )

        return [
            RankedItem(id=str(c.id), title=c.title, slug=c.slug, count=c.count, revenue=0)
            for c in top_courses_query
        ]

    @staticmethod
    def get_rankings(db: Session, limit: int = 10) -> RankingsResponse:
        """Get rankings for packages and courses.

        Args:
            db: Database session.
            limit: Maximum number of items in each ranking.

        Returns:
            RankingsResponse with package and course rankings.
        """
        # Package rankings with full details
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

        # Course rankings with completion rates
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

    @staticmethod
    def get_sales_windows_stats(db: Session) -> SalesWindowsResponse:
        """Get statistics for sales windows.

        Args:
            db: Database session.

        Returns:
            SalesWindowsResponse with per-window statistics.
        """
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
