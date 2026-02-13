from datetime import UTC, date, datetime
from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.courses.models import Achievement, PointsHistory, UserAchievement, UserPoints, UserStreak


class GamificationService:
    POINTS_LESSON_COMPLETED = 10
    POINTS_COURSE_COMPLETED = 100

    STREAK_DAILY_BONUS = {
        1: 2,
        3: 5,
        7: 10,
        14: 15,
        30: 25,
    }

    LEVEL_THRESHOLDS = [
        0,
        100,
        250,
        500,
        1000,
        2000,
        4000,
        7500,
        12500,
        20000,
    ]

    @staticmethod
    def _get_streak_bonus(current_streak: int) -> int:
        """Return daily XP bonus for the given streak length."""
        bonus = 0
        for threshold in sorted(GamificationService.STREAK_DAILY_BONUS.keys()):
            if current_streak >= threshold:
                bonus = GamificationService.STREAK_DAILY_BONUS[threshold]
            else:
                break
        return bonus

    @staticmethod
    def _award_streak_bonus(user_id: UUID, current_streak: int, db: Session) -> None:
        """Award daily streak bonus XP."""
        bonus = GamificationService._get_streak_bonus(current_streak)
        if bonus > 0:
            GamificationService.award_points(
                user_id=user_id,
                points=bonus,
                reason=f"Daily streak bonus (day {current_streak})",
                db=db,
                reference_type="streak",
                reference_id=None,
            )

    @staticmethod
    def update_streak(user_id: UUID, db: Session) -> UserStreak:
        """
        Update user streak with 24h grace period.
        Grace period: user can skip 1 day once every 30 days.
        """
        today = date.today()

        user_streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()

        if not user_streak:
            user_streak = UserStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=today,
                grace_period_used_at=None,
            )
            db.add(user_streak)
            db.commit()
            db.refresh(user_streak)

            GamificationService._award_streak_bonus(user_id, 1, db)
            GamificationService.check_streak_achievements(user_id, 1, db)
            return cast(UserStreak, user_streak)

        last_activity = user_streak.last_activity_date
        days_since_last = (today - last_activity).days

        if days_since_last == 0:
            return cast(UserStreak, user_streak)

        if days_since_last == 1:
            user_streak.current_streak += 1
            user_streak.longest_streak = max(user_streak.longest_streak, user_streak.current_streak)
            user_streak.last_activity_date = today
            db.commit()

            GamificationService._award_streak_bonus(user_id, user_streak.current_streak, db)
            GamificationService.check_streak_achievements(user_id, user_streak.current_streak, db)
            return cast(UserStreak, user_streak)

        if days_since_last == 2:
            grace_available = (
                user_streak.grace_period_used_at is None
                or (today - user_streak.grace_period_used_at).days >= 30
            )

            if grace_available:
                user_streak.current_streak += 1
                user_streak.longest_streak = max(
                    user_streak.longest_streak, user_streak.current_streak
                )
                user_streak.last_activity_date = today
                user_streak.grace_period_used_at = today
                db.commit()

                GamificationService._award_streak_bonus(user_id, user_streak.current_streak, db)
                GamificationService.check_streak_achievements(
                    user_id, user_streak.current_streak, db
                )
                return cast(UserStreak, user_streak)
            else:
                user_streak.current_streak = 1
                user_streak.last_activity_date = today
                db.commit()
                return cast(UserStreak, user_streak)

        if days_since_last > 2:
            user_streak.current_streak = 1
            user_streak.last_activity_date = today
            db.commit()
            return cast(UserStreak, user_streak)

        return cast(UserStreak, user_streak)

    @staticmethod
    def check_streak_achievements(user_id: UUID, current_streak: int, db: Session) -> None:
        """Check and award streak achievements."""
        streak_achievements = {
            3: "streak_3_days",
            7: "streak_7_days",
            14: "streak_14_days",
            30: "streak_30_days",
            60: "streak_60_days",
            100: "streak_100_days",
        }

        if current_streak in streak_achievements:
            achievement_code = streak_achievements[current_streak]
            achievement = db.query(Achievement).filter(Achievement.code == achievement_code).first()

            if achievement:
                existing = (
                    db.query(UserAchievement)
                    .filter(
                        UserAchievement.user_id == user_id,
                        UserAchievement.achievement_id == achievement.id,
                    )
                    .first()
                )

                if not existing:
                    user_achievement = UserAchievement(
                        user_id=user_id,
                        achievement_id=achievement.id,
                        earned_at=datetime.now(UTC),
                    )
                    db.add(user_achievement)

                    GamificationService.award_points(
                        user_id=user_id,
                        points=achievement.points_reward,
                        reason=f"Achievement: {achievement.title}",
                        db=db,
                        reference_type="achievement",
                        reference_id=achievement.id,
                    )

                    db.commit()

    @staticmethod
    def award_points(
        user_id: UUID,
        points: int,
        reason: str,
        db: Session,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> UserPoints:
        """Award points to a user and update their level."""
        user_points = db.query(UserPoints).filter(UserPoints.user_id == user_id).first()

        if not user_points:
            user_points = UserPoints(user_id=user_id, total_points=0, level=1)
            db.add(user_points)

        user_points.total_points += points

        new_level = GamificationService.calculate_level(user_points.total_points)
        user_points.level = new_level

        points_history = PointsHistory(
            user_id=user_id,
            points=points,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=datetime.now(UTC),
        )
        db.add(points_history)

        db.commit()
        db.refresh(user_points)

        return cast(UserPoints, user_points)

    @staticmethod
    def calculate_level(total_points: int) -> int:
        """Calculate user level based on total points."""
        for level in range(len(GamificationService.LEVEL_THRESHOLDS) - 1, 0, -1):
            if total_points >= GamificationService.LEVEL_THRESHOLDS[level]:
                return level + 1
        return 1

    @staticmethod
    def points_to_next_level(total_points: int) -> int:
        """Calculate points needed for next level."""
        current_level = GamificationService.calculate_level(total_points)

        if current_level >= len(GamificationService.LEVEL_THRESHOLDS):
            return 0

        next_level_threshold = GamificationService.LEVEL_THRESHOLDS[current_level]
        return next_level_threshold - total_points

    @staticmethod
    def check_lesson_completion_achievement(user_id: UUID, db: Session) -> None:
        """Check and award first lesson completion achievement."""
        achievement = (
            db.query(Achievement).filter(Achievement.code == "first_lesson_completed").first()
        )

        if achievement:
            existing = (
                db.query(UserAchievement)
                .filter(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement.id,
                )
                .first()
            )

            if not existing:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    earned_at=datetime.now(UTC),
                )
                db.add(user_achievement)

                GamificationService.award_points(
                    user_id=user_id,
                    points=achievement.points_reward,
                    reason=f"Achievement: {achievement.title}",
                    reference_type="achievement",
                    reference_id=achievement.id,
                    db=db,
                )

                db.commit()

    @staticmethod
    def check_course_completion_achievement(user_id: UUID, course_slug: str, db: Session) -> None:
        """Check and award course completion achievement."""
        achievement_code = f"course_completed_{course_slug}"
        achievement = db.query(Achievement).filter(Achievement.code == achievement_code).first()

        if achievement:
            existing = (
                db.query(UserAchievement)
                .filter(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement.id,
                )
                .first()
            )

            if not existing:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    earned_at=datetime.now(UTC),
                )
                db.add(user_achievement)

                GamificationService.award_points(
                    user_id=user_id,
                    points=achievement.points_reward,
                    reason=f"Achievement: {achievement.title}",
                    reference_type="achievement",
                    reference_id=achievement.id,
                    db=db,
                )

                db.commit()
