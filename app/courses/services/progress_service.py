import calendar
from datetime import UTC, date, datetime, timedelta
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.models.user_daily_activity import UserDailyActivity
from app.courses.models import Course, Enrollment, Lesson, LessonProgress, Module
from app.courses.models.gamification import PointsHistory, UserStreak
from app.courses.services.gamification_service import GamificationService


class ProgressService:
    COMPLETION_THRESHOLD = 95

    @staticmethod
    def update_lesson_progress(
        user_id: UUID,
        lesson_id: UUID,
        watched_seconds: int,
        last_position_seconds: int,
        completion_percentage: int,
        db: Session,
    ) -> LessonProgress:
        """Update user's progress for a lesson."""
        progress = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
            .first()
        )

        if not progress:
            progress = LessonProgress(user_id=user_id, lesson_id=lesson_id)
            db.add(progress)

        was_completed = progress.is_completed

        progress.watched_seconds = watched_seconds
        progress.last_position_seconds = last_position_seconds
        progress.completion_percentage = completion_percentage
        progress.last_updated_at = datetime.now(UTC)

        if (
            completion_percentage >= ProgressService.COMPLETION_THRESHOLD
            and not progress.is_completed
        ):
            progress.is_completed = True
            progress.completed_at = datetime.now(UTC)

            GamificationService.award_points(
                user_id=user_id,
                points=GamificationService.POINTS_LESSON_COMPLETED,
                reason="Lesson completed",
                db=db,
                reference_type="lesson",
                reference_id=lesson_id,
            )

            if not was_completed:
                GamificationService.check_lesson_completion_achievement(user_id, db)

            ProgressService.check_course_completion(user_id, lesson_id, db)

        if watched_seconds >= 60 or completion_percentage >= ProgressService.COMPLETION_THRESHOLD:
            GamificationService.update_streak(user_id, db)

        db.commit()
        db.refresh(progress)

        return cast(LessonProgress, progress)

    @staticmethod
    def check_course_completion(user_id: UUID, lesson_id: UUID, db: Session) -> None:
        """Check if user completed entire course and update enrollment."""
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return

        module = db.query(Module).filter(Module.id == lesson.module_id).first()
        if not module:
            return

        course = db.query(Course).filter(Course.id == module.course_id).first()
        if not course:
            return

        all_lesson_ids = (
            db.query(Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .filter(Module.course_id == course.id)
            .all()
        )
        all_lesson_ids = [lid[0] for lid in all_lesson_ids]

        completed_lessons = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(all_lesson_ids),
                LessonProgress.is_completed,
            )
            .count()
        )

        if completed_lessons == len(all_lesson_ids):
            enrollment = (
                db.query(Enrollment)
                .filter(Enrollment.user_id == user_id, Enrollment.course_id == course.id)
                .first()
            )

            if enrollment and not enrollment.completed_at:
                enrollment.completed_at = datetime.now(UTC)

                GamificationService.award_points(
                    user_id=user_id,
                    points=GamificationService.POINTS_COURSE_COMPLETED,
                    reason=f"Course completed: {course.title}",
                    db=db,
                    reference_type="course",
                    reference_id=course.id,
                )

                GamificationService.check_course_completion_achievement(user_id, course.slug, db)

                db.commit()

    @staticmethod
    def mark_lesson_complete(user_id: UUID, lesson_id: UUID, db: Session) -> LessonProgress:
        """Manually mark a lesson as complete."""
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        is_text_only = lesson.mux_playback_id is None or lesson.duration_seconds == 0

        progress = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
            .first()
        )

        if not progress:
            if is_text_only:
                progress = LessonProgress(user_id=user_id, lesson_id=lesson_id)
                db.add(progress)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Musisz najpierw rozpocząć oglądanie lekcji wideo, "
                        "aby móc ją oznaczyć jako ukończoną"
                    ),
                )

        threshold = ProgressService.COMPLETION_THRESHOLD
        if not is_text_only and progress.completion_percentage < threshold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Musisz obejrzeć co najmniej {threshold}% lekcji wideo, "
                    f"aby móc ją oznaczyć jako ukończoną "
                    f"(obecny postęp: {progress.completion_percentage}%)"
                ),
            )

        progress.completion_percentage = 100

        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.now(UTC)

            GamificationService.award_points(
                user_id=user_id,
                points=GamificationService.POINTS_LESSON_COMPLETED,
                reason="Lesson completed",
                db=db,
                reference_type="lesson",
                reference_id=lesson_id,
            )

            GamificationService.check_lesson_completion_achievement(user_id, db)

            ProgressService.check_course_completion(user_id, lesson_id, db)

            GamificationService.update_streak(user_id, db)

        db.commit()
        db.refresh(progress)

        return cast(LessonProgress, progress)

    @staticmethod
    def mark_lesson_uncomplete(user_id: UUID, lesson_id: UUID, db: Session) -> LessonProgress:
        """Mark a completed lesson as uncomplete."""
        progress = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
            .first()
        )

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nie znaleziono postępu dla tej lekcji",
            )

        if not progress.is_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ta lekcja nie jest oznaczona jako ukończona",
            )

        progress.is_completed = False
        progress.completed_at = None

        db.commit()
        db.refresh(progress)

        return cast(LessonProgress, progress)

    @staticmethod
    def get_course_progress_summary(user_id: UUID, course_id: UUID, db: Session) -> dict:
        """Get user's progress summary for a course."""
        lesson_id_rows = (
            db.query(Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .filter(Module.course_id == course_id)
            .all()
        )
        lesson_ids: list[UUID] = [lid[0] for lid in lesson_id_rows]

        total_lessons = len(lesson_ids)

        progress_records = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(lesson_ids),
            )
            .all()
        )

        progress_by_lesson = {p.lesson_id: p for p in progress_records}
        lessons_progress = []
        for lid in lesson_ids:
            progress = progress_by_lesson.get(lid)
            if progress:
                lessons_progress.append(
                    {
                        "lesson_id": str(lid),
                        "watched_seconds": progress.watched_seconds,
                        "last_position_seconds": progress.last_position_seconds,
                        "completion_percentage": progress.completion_percentage,
                        "is_completed": progress.is_completed,
                        "completed_at": progress.completed_at,
                        "last_updated_at": progress.last_updated_at,
                    }
                )
            else:
                lessons_progress.append(
                    {
                        "lesson_id": str(lid),
                        "watched_seconds": 0,
                        "last_position_seconds": 0,
                        "completion_percentage": 0,
                        "is_completed": False,
                        "completed_at": None,
                        "last_updated_at": None,
                    }
                )

        completed_lessons = sum(1 for p in progress_records if p.is_completed)
        total_watch_time_seconds = sum(p.watched_seconds for p in progress_records)

        progress_percentage = (
            int(completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        )

        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )

        return {
            "course_id": str(course_id),
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "progress_percentage": progress_percentage,
            "total_watch_time_seconds": total_watch_time_seconds,
            "last_accessed_at": enrollment.last_accessed_at if enrollment else None,
            "lessons": lessons_progress,
        }

    @staticmethod
    def get_weekly_stats(user_id: UUID, db: Session) -> dict:
        """Get user's learning stats for the current week (Monday–Sunday)."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_start_dt = datetime.combine(week_start, datetime.min.time())

        active_date_rows = (
            db.query(UserDailyActivity.date)
            .filter(
                UserDailyActivity.user_id == user_id,
                UserDailyActivity.date >= week_start,
                UserDailyActivity.date <= week_end,
            )
            .distinct()
            .all()
        )
        active_dates = [row[0] for row in active_date_rows]
        active_days = len(active_dates)

        total_watched_seconds = (
            db.query(func.coalesce(func.sum(LessonProgress.watched_seconds), 0))
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.last_updated_at >= week_start_dt,
            )
            .scalar()
        ) or 0

        lessons_completed = (
            db.query(func.count())
            .select_from(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.is_completed == True,  # noqa: E712
                LessonProgress.completed_at >= week_start_dt,
            )
            .scalar()
        ) or 0

        points_earned = (
            db.query(func.coalesce(func.sum(PointsHistory.points), 0))
            .filter(
                PointsHistory.user_id == user_id,
                PointsHistory.created_at >= week_start_dt,
            )
            .scalar()
        ) or 0

        streak_record = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
        current_streak = streak_record.current_streak if streak_record else 0
        longest_streak = streak_record.longest_streak if streak_record else 0

        return {
            "week_start": week_start,
            "week_end": week_end,
            "active_days": active_days,
            "learning_minutes": total_watched_seconds // 60,
            "lessons_completed": lessons_completed,
            "points_earned": points_earned,
            "current_streak": current_streak,
            "active_dates": sorted(active_dates),
            "longest_streak": longest_streak,
        }

    @staticmethod
    def get_monthly_activity_dates(user_id: UUID, year: int, month: int, db: Session) -> dict:
        """Get all active dates for a given month."""
        month_start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        month_end = date(year, month, last_day)

        rows = (
            db.query(UserDailyActivity.date)
            .filter(
                UserDailyActivity.user_id == user_id,
                UserDailyActivity.date >= month_start,
                UserDailyActivity.date <= month_end,
            )
            .distinct()
            .all()
        )

        return {
            "year": year,
            "month": month,
            "active_dates": sorted(row[0] for row in rows),
        }
