"""
E2E tests for gamification system (achievements, points, streaks).
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.courses.services.gamification_service import GamificationService


class TestGetStreakBonus:
    """Unit tests for _get_streak_bonus threshold logic."""

    def test_day_1_returns_2(self):
        assert GamificationService._get_streak_bonus(1) == 2

    def test_day_2_returns_2(self):
        assert GamificationService._get_streak_bonus(2) == 2

    def test_day_3_returns_5(self):
        assert GamificationService._get_streak_bonus(3) == 5

    def test_day_6_returns_5(self):
        assert GamificationService._get_streak_bonus(6) == 5

    def test_day_7_returns_10(self):
        assert GamificationService._get_streak_bonus(7) == 10

    def test_day_13_returns_10(self):
        assert GamificationService._get_streak_bonus(13) == 10

    def test_day_14_returns_15(self):
        assert GamificationService._get_streak_bonus(14) == 15

    def test_day_29_returns_15(self):
        assert GamificationService._get_streak_bonus(29) == 15

    def test_day_30_returns_25(self):
        assert GamificationService._get_streak_bonus(30) == 25

    def test_day_100_returns_25(self):
        assert GamificationService._get_streak_bonus(100) == 25

    def test_day_0_returns_0(self):
        assert GamificationService._get_streak_bonus(0) == 0


@pytest.mark.asyncio
async def test_get_user_gamification_data(
    test_client: AsyncClient, test_user_token, db_session, test_user
):
    """Test getting user's gamification data."""
    from app.courses.models import UserPoints, UserStreak

    # Create user points
    user_points = UserPoints(
        user_id=test_user.id,
        total_points=500,
        level=3,
    )
    db_session.add(user_points)

    # Create user streak
    user_streak = UserStreak(
        user_id=test_user.id,
        current_streak=7,
        longest_streak=10,
        last_activity_date=date.today(),
    )
    db_session.add(user_streak)
    db_session.flush()

    response = await test_client.get(
        "/api/v1/gamification/me",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["points"]["total_points"] == 500
    assert data["points"]["level"] == 3
    assert data["streak"]["current_streak"] == 7
    assert data["streak"]["longest_streak"] == 10


@pytest.mark.asyncio
async def test_get_available_achievements(
    test_client: AsyncClient, test_user_token, test_achievement
):
    """Test getting list of available achievements."""
    response = await test_client.get(
        "/api/v1/gamification/achievements",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least the test achievement
    assert len(data) > 0


@pytest.mark.asyncio
async def test_get_user_achievements(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_achievement,
    db_session,
):
    """Test getting user's earned achievements."""
    from datetime import datetime

    from app.courses.models import UserAchievement

    # Award achievement to user
    user_achievement = UserAchievement(
        user_id=test_user.id,
        achievement_id=test_achievement.id,
        earned_at=datetime.utcnow(),
    )
    db_session.add(user_achievement)
    db_session.flush()

    response = await test_client.get(
        "/api/v1/gamification/achievements/me",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["achievement"]["code"] == "test_achievement"


@pytest.mark.asyncio
async def test_points_awarded_on_lesson_completion(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test points are awarded when lesson is completed."""
    from app.courses.models import UserPoints

    # Initialize user points
    user_points = UserPoints(
        user_id=test_user.id,
        total_points=0,
        level=1,
    )
    db_session.add(user_points)
    db_session.flush()

    initial_points = 0

    # Complete lesson (95%+)
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 290,
            "last_position_seconds": 290,
            "completion_percentage": 97,
        },
        cookies={"access_token": test_user_token},
    )

    # Check points increased
    db_session.refresh(user_points)
    assert user_points.total_points > initial_points


@pytest.mark.asyncio
async def test_streak_updates_on_activity(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test streak updates when user has daily activity."""
    from app.courses.models import UserStreak

    # Create initial streak
    user_streak = UserStreak(
        user_id=test_user.id,
        current_streak=3,
        longest_streak=5,
        last_activity_date=date.today() - timedelta(days=1),
    )
    db_session.add(user_streak)
    db_session.flush()

    # Update progress (triggers streak update)
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 60,
            "last_position_seconds": 60,
            "completion_percentage": 20,
        },
        cookies={"access_token": test_user_token},
    )

    # Check streak incremented
    db_session.refresh(user_streak)
    assert user_streak.current_streak == 4
    assert user_streak.last_activity_date == date.today()


@pytest.mark.asyncio
async def test_streak_resets_after_gap(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test streak resets after >2 days gap."""
    from app.courses.models import UserStreak

    # Create streak with 3 day gap
    user_streak = UserStreak(
        user_id=test_user.id,
        current_streak=10,
        longest_streak=15,
        last_activity_date=date.today() - timedelta(days=3),
    )
    db_session.add(user_streak)
    db_session.flush()

    # Update progress
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 60,
            "last_position_seconds": 60,
            "completion_percentage": 20,
        },
        cookies={"access_token": test_user_token},
    )

    # Check streak reset to 1
    db_session.refresh(user_streak)
    assert user_streak.current_streak == 1
    assert user_streak.longest_streak == 15  # Longest unchanged


@pytest.mark.asyncio
async def test_grace_period_preserves_streak(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test 24h grace period preserves streak."""
    from app.courses.models import UserStreak

    # Create streak with 2 day gap (within grace period)
    user_streak = UserStreak(
        user_id=test_user.id,
        current_streak=7,
        longest_streak=10,
        last_activity_date=date.today() - timedelta(days=2),
        grace_period_used_at=None,  # Grace available
    )
    db_session.add(user_streak)
    db_session.flush()

    # Update progress
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 60,
            "last_position_seconds": 60,
            "completion_percentage": 20,
        },
        cookies={"access_token": test_user_token},
    )

    # Check streak preserved and incremented
    db_session.refresh(user_streak)
    assert user_streak.current_streak == 8
    assert user_streak.grace_period_used_at == date.today()


@pytest.mark.asyncio
async def test_level_up_on_points_threshold(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test user levels up at point thresholds."""
    from app.courses.models import UserPoints

    # Set user just below level 2 threshold (100 points)
    user_points = UserPoints(
        user_id=test_user.id,
        total_points=95,
        level=1,
    )
    db_session.add(user_points)
    db_session.flush()

    # Complete lesson to get 10 points (total 105)
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 290,
            "last_position_seconds": 290,
            "completion_percentage": 97,
        },
        cookies={"access_token": test_user_token},
    )

    # Check level increased
    db_session.refresh(user_points)
    assert user_points.level >= 2


@pytest.mark.asyncio
async def test_points_history_tracked(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test points history is tracked."""
    from app.courses.models import PointsHistory, UserPoints

    # Initialize points
    user_points = UserPoints(
        user_id=test_user.id,
        total_points=0,
        level=1,
    )
    db_session.add(user_points)
    db_session.flush()

    # Complete lesson
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 290,
            "last_position_seconds": 290,
            "completion_percentage": 97,
        },
        cookies={"access_token": test_user_token},
    )

    # Check points history created
    history = db_session.query(PointsHistory).filter(PointsHistory.user_id == test_user.id).all()

    assert len(history) > 0
    assert history[0].points == 10  # 10 points for lesson completion
    assert "lesson completed" in history[0].reason.lower()


@pytest.mark.asyncio
async def test_streak_bonus_awarded_on_streak_increment(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_lesson,
    test_enrollment,
    db_session,
):
    """Test daily streak bonus XP is awarded when streak increments."""
    from app.courses.models import PointsHistory, UserPoints, UserStreak

    # Initialize user points
    user_points = UserPoints(
        user_id=test_user.id,
        total_points=0,
        level=1,
    )
    db_session.add(user_points)

    # Create streak with last activity yesterday (will increment today)
    user_streak = UserStreak(
        user_id=test_user.id,
        current_streak=6,
        longest_streak=6,
        last_activity_date=date.today() - timedelta(days=1),
    )
    db_session.add(user_streak)
    db_session.flush()

    # Trigger activity (updates streak)
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 60,
            "last_position_seconds": 60,
            "completion_percentage": 20,
        },
        cookies={"access_token": test_user_token},
    )

    # Check streak incremented to 7
    db_session.refresh(user_streak)
    assert user_streak.current_streak == 7

    # Check points history contains streak bonus entry
    history = (
        db_session.query(PointsHistory)
        .filter(
            PointsHistory.user_id == test_user.id,
            PointsHistory.reference_type == "streak",
        )
        .all()
    )
    assert len(history) == 1
    assert "Daily streak bonus" in history[0].reason
    assert history[0].points == 10  # Day 7 → +10 XP bonus
