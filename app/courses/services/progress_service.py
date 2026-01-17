from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.courses.models import Course, Enrollment, Lesson, LessonProgress, Module
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
        progress.last_updated_at = datetime.utcnow()

        if (
            completion_percentage >= ProgressService.COMPLETION_THRESHOLD
            and not progress.is_completed
        ):
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()

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
                enrollment.completed_at = datetime.utcnow()

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
        progress = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
            .first()
        )

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progress record not found",
            )

        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
            progress.completion_percentage = 100

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
    def get_course_progress_summary(user_id: UUID, course_id: UUID, db: Session) -> dict:
        """Get user's progress summary for a course."""
        lesson_ids = (
            db.query(Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .filter(Module.course_id == course_id)
            .all()
        )
        lesson_ids = [lid[0] for lid in lesson_ids]

        total_lessons = len(lesson_ids)

        completed_lessons = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(lesson_ids),
                LessonProgress.is_completed,
            )
            .count()
        )

        total_watch_time = (
            db.query(LessonProgress)
            .filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id.in_(lesson_ids))
            .with_entities(LessonProgress.watched_seconds)
            .all()
        )
        total_watch_time_seconds = sum(wt[0] for wt in total_watch_time)

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
        }
