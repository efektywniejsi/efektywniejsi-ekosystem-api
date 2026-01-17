from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.models import Achievement, UserAchievement, UserPoints, UserStreak
from app.courses.schemas.gamification import (
    AchievementResponse,
    GamificationSummaryResponse,
    UserAchievementResponse,
    UserPointsResponse,
    UserStreakResponse,
)
from app.courses.services.gamification_service import GamificationService
from app.db.session import get_db

router = APIRouter()


@router.get("/gamification/me", response_model=GamificationSummaryResponse)
async def get_my_gamification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GamificationSummaryResponse:
    """Get gamification summary for current user."""
    user_points = db.query(UserPoints).filter(UserPoints.user_id == current_user.id).first()

    if not user_points:
        user_points = UserPoints(user_id=current_user.id, total_points=0, level=1)
        db.add(user_points)
        db.commit()
        db.refresh(user_points)

    user_streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()

    if not user_streak:
        user_streak = UserStreak(
            user_id=current_user.id,
            current_streak=0,
            longest_streak=0,
            last_activity_date=date.today(),
        )
        db.add(user_streak)
        db.commit()
        db.refresh(user_streak)

    recent_achievements = (
        db.query(UserAchievement)
        .options(joinedload(UserAchievement.achievement))
        .filter(UserAchievement.user_id == current_user.id)
        .order_by(UserAchievement.earned_at.desc())
        .limit(3)
        .all()
    )

    total_earned = (
        db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).count()
    )
    total_available = db.query(Achievement).filter(Achievement.is_active).count()

    grace_available = True
    days_until_grace = 0

    if user_streak.grace_period_used_at:
        days_since_grace = (date.today() - user_streak.grace_period_used_at).days
        if days_since_grace < 30:
            grace_available = False
            days_until_grace = 30 - days_since_grace

    points_to_next = GamificationService.points_to_next_level(user_points.total_points)

    return GamificationSummaryResponse(
        points=UserPointsResponse(
            id=str(user_points.id),
            user_id=str(user_points.user_id),
            total_points=user_points.total_points,
            level=user_points.level,
            points_to_next_level=points_to_next,
            created_at=user_points.created_at,
            updated_at=user_points.updated_at,
        ),
        streak=UserStreakResponse(
            id=str(user_streak.id),
            user_id=str(user_streak.user_id),
            current_streak=user_streak.current_streak,
            longest_streak=user_streak.longest_streak,
            last_activity_date=user_streak.last_activity_date,
            grace_period_used_at=user_streak.grace_period_used_at,
            grace_period_available=grace_available,
            days_until_grace_available=days_until_grace,
        ),
        recent_achievements=[
            UserAchievementResponse(
                id=str(ua.id),
                user_id=str(ua.user_id),
                achievement_id=str(ua.achievement_id),
                earned_at=ua.earned_at,
                progress_value=ua.progress_value,
                achievement=AchievementResponse(
                    id=str(ua.achievement.id),
                    code=ua.achievement.code,
                    title=ua.achievement.title,
                    description=ua.achievement.description,
                    icon=ua.achievement.icon,
                    points_reward=ua.achievement.points_reward,
                    category=ua.achievement.category,
                    is_active=ua.achievement.is_active,
                    created_at=ua.achievement.created_at,
                ),
            )
            for ua in recent_achievements
        ],
        total_achievements_earned=total_earned,
        total_achievements_available=total_available,
    )


@router.get("/gamification/achievements", response_model=list[AchievementResponse])
async def get_all_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AchievementResponse]:
    """Get all available achievements."""
    achievements = db.query(Achievement).filter(Achievement.is_active).all()

    return [
        AchievementResponse(
            id=str(a.id),
            code=a.code,
            title=a.title,
            description=a.description,
            icon=a.icon,
            points_reward=a.points_reward,
            category=a.category,
            is_active=a.is_active,
            created_at=a.created_at,
        )
        for a in achievements
    ]


@router.get("/gamification/achievements/me", response_model=list[UserAchievementResponse])
async def get_my_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserAchievementResponse]:
    """Get all achievements earned by current user."""
    user_achievements = (
        db.query(UserAchievement)
        .options(joinedload(UserAchievement.achievement))
        .filter(UserAchievement.user_id == current_user.id)
        .order_by(UserAchievement.earned_at.desc())
        .all()
    )

    return [
        UserAchievementResponse(
            id=str(ua.id),
            user_id=str(ua.user_id),
            achievement_id=str(ua.achievement_id),
            earned_at=ua.earned_at,
            progress_value=ua.progress_value,
            achievement=AchievementResponse(
                id=str(ua.achievement.id),
                code=ua.achievement.code,
                title=ua.achievement.title,
                description=ua.achievement.description,
                icon=ua.achievement.icon,
                points_reward=ua.achievement.points_reward,
                category=ua.achievement.category,
                is_active=ua.achievement.is_active,
                created_at=ua.achievement.created_at,
            ),
        )
        for ua in user_achievements
    ]
