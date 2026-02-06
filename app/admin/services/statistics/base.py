"""Base utilities and helpers for statistics services."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.models.user_daily_activity import UserDailyActivity


def get_period_boundaries(period: str) -> tuple[datetime, datetime]:
    """Get start and end datetime for a period.

    Args:
        period: One of 'today', 'this_week', 'this_month', 'last_30_days',
                'last_90_days', 'this_year'. Defaults to 'last_30_days'.

    Returns:
        Tuple of (start_datetime, end_datetime) in UTC.
    """
    now = datetime.now(UTC)
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


def get_previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Get the previous period of the same duration.

    Args:
        start: Start of current period.
        end: End of current period.

    Returns:
        Tuple of (previous_start, previous_end) where duration matches input.
    """
    duration = end - start
    return start - duration, start


def calculate_change_percent(current: int | float, previous: int | float) -> float:
    """Calculate percentage change between two values.

    Args:
        current: Current period value.
        previous: Previous period value.

    Returns:
        Percentage change rounded to 2 decimal places.
        Returns 100.0 if previous is 0 and current > 0.
        Returns 0.0 if both are 0.
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


def count_active_users(
    db: Session,
    since: datetime,
    until: datetime | None = None,
) -> int:
    """Count distinct active users from daily activity log.

    Args:
        db: Database session.
        since: Count activity from this datetime.
        until: Count activity until this datetime (exclusive). If None, no upper bound.

    Returns:
        Number of distinct active users in the period.
    """
    query = db.query(func.count(func.distinct(UserDailyActivity.user_id))).filter(
        UserDailyActivity.date >= since.date()
    )
    if until is not None:
        query = query.filter(UserDailyActivity.date < until.date())
    return query.scalar() or 0
