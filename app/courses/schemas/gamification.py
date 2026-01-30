from datetime import date, datetime

from pydantic import BaseModel


class AchievementResponse(BaseModel):
    id: str
    code: str
    title: str
    description: str
    icon: str | None = None
    points_reward: int
    category: str | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserAchievementResponse(BaseModel):
    id: str
    user_id: str
    achievement_id: str
    earned_at: datetime
    progress_value: int | None = None
    achievement: AchievementResponse

    class Config:
        from_attributes = True


class UserStreakResponse(BaseModel):
    id: str
    user_id: str
    current_streak: int
    longest_streak: int
    last_activity_date: date
    grace_period_used_at: date | None = None
    grace_period_available: bool = True
    days_until_grace_available: int = 0

    class Config:
        from_attributes = True


class UserPointsResponse(BaseModel):
    id: str
    user_id: str
    total_points: int
    level: int
    points_to_next_level: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GamificationSummaryResponse(BaseModel):
    points: UserPointsResponse
    streak: UserStreakResponse
    recent_achievements: list[UserAchievementResponse]
    total_achievements_earned: int
    total_achievements_available: int
