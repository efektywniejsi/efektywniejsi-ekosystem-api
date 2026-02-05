"""User statistics service."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    DailyUserDetailsResponse,
    MonthlyUsersResponse,
    UserActivityDataPoint,
    UserDetail,
    UsersKPI,
    UserStatisticsResponse,
)
from app.admin.services.statistics.base import count_active_users
from app.auth.models.user import User
from app.auth.models.user_daily_activity import UserDailyActivity
from app.courses.models.enrollment import Enrollment


class UserStatisticsService:
    """Service for user-related statistics."""

    @staticmethod
    def get_kpis(
        db: Session, today_start: datetime, week_start: datetime, month_start: datetime
    ) -> UsersKPI:
        """Get user KPIs for dashboard.

        Args:
            db: Database session.
            today_start: Start of today.
            week_start: Start of current week.
            month_start: Start of current month.

        Returns:
            UsersKPI with total, new, and active user counts.
        """
        total_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712
        new_users_month = db.query(User).filter(User.created_at >= month_start).count()

        active_today = count_active_users(db, today_start)
        active_week = count_active_users(db, week_start)

        return UsersKPI(
            total=total_users,
            new_this_month=new_users_month,
            active_today=active_today,
            active_this_week=active_week,
        )

    @staticmethod
    def get_statistics(db: Session, days: int = 30) -> UserStatisticsResponse:
        """Get user statistics with activity trends.

        Args:
            db: Database session.
            days: Number of days for the activity trend data.

        Returns:
            UserStatisticsResponse with user counts and activity data points.
        """
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        period_start = today_start - timedelta(days=days)

        total_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712

        # Active users counts
        active_today = count_active_users(db, today_start)
        active_week = count_active_users(db, week_start)
        active_month = count_active_users(db, month_start)

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
        activity_by_day = {row[0]: row[1] for row in activity_rows}

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

    @staticmethod
    def get_daily_details(
        db: Session, date: str, user_type: str, limit: int = 50
    ) -> DailyUserDetailsResponse:
        """Get list of active or new users for a specific day.

        Args:
            db: Database session.
            date: Date string in YYYY-MM-DD format.
            user_type: Either 'active' or 'new'.
            limit: Maximum number of users to return.

        Returns:
            DailyUserDetailsResponse with user list and totals.
        """
        target_date = datetime.strptime(date, "%Y-%m-%d")
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        users_list: list[UserDetail] = []
        total = 0

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

            total = (
                db.query(User)
                .filter(
                    User.created_at >= day_start,
                    User.created_at < day_end,
                )
                .count()
            )

        return DailyUserDetailsResponse(
            date=date,
            type=user_type,
            total=total,
            users=users_list,
        )

    @staticmethod
    def get_monthly_new_users(db: Session, limit: int = 50) -> MonthlyUsersResponse:
        """Get new users registered in the current month.

        Args:
            db: Database session.
            limit: Maximum number of users to return.

        Returns:
            MonthlyUsersResponse with total count and user list.
        """
        now = datetime.now(UTC)
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
        last_activity_map: dict[UUID, datetime] = {}
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
