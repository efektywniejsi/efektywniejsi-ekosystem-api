from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.dependencies import RequireLessonEnrollment
from app.courses.models import LessonProgress
from app.courses.schemas.progress import (
    CourseProgressSummary,
    LessonProgressResponse,
    MonthlyActivityResponse,
    ProgressUpdateRequest,
    WeeklyStatsResponse,
)
from app.courses.services.progress_service import ProgressService
from app.db.session import get_db

router = APIRouter()


@router.get("/progress/weekly-stats", response_model=WeeklyStatsResponse)
async def get_weekly_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeeklyStatsResponse:
    """Get learning stats for the current week."""
    stats = ProgressService.get_weekly_stats(current_user.id, db)
    return WeeklyStatsResponse(**stats)


@router.get("/progress/activity-dates", response_model=MonthlyActivityResponse)
async def get_monthly_activity_dates(
    year: int = Query(default_factory=lambda: date.today().year, ge=2020, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyActivityResponse:
    """Get all active dates for a given month."""
    result = ProgressService.get_monthly_activity_dates(current_user.id, year, month, db)
    return MonthlyActivityResponse(**result)


@router.post(
    "/progress/lessons/{lesson_id}",
    response_model=LessonProgressResponse,
    dependencies=[Depends(RequireLessonEnrollment())],
)
async def update_lesson_progress(
    lesson_id: UUID,
    request: ProgressUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressResponse:
    """Update progress for a lesson."""
    progress = ProgressService.update_lesson_progress(
        user_id=current_user.id,
        lesson_id=lesson_id,
        watched_seconds=request.watched_seconds,
        last_position_seconds=request.last_position_seconds,
        completion_percentage=request.completion_percentage,
        db=db,
    )

    return LessonProgressResponse(
        id=str(progress.id),
        user_id=str(progress.user_id),
        lesson_id=str(progress.lesson_id),
        watched_seconds=progress.watched_seconds,
        last_position_seconds=progress.last_position_seconds,
        completion_percentage=progress.completion_percentage,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
        last_updated_at=progress.last_updated_at,
    )


@router.get("/progress/lessons/{lesson_id}", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressResponse:
    """Get progress for a specific lesson."""
    progress = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == current_user.id, LessonProgress.lesson_id == lesson_id)
        .first()
    )

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress not found",
        )

    return LessonProgressResponse(
        id=str(progress.id),
        user_id=str(progress.user_id),
        lesson_id=str(progress.lesson_id),
        watched_seconds=progress.watched_seconds,
        last_position_seconds=progress.last_position_seconds,
        completion_percentage=progress.completion_percentage,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
        last_updated_at=progress.last_updated_at,
    )


@router.get("/progress/courses/{course_id}", response_model=CourseProgressSummary)
async def get_course_progress(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseProgressSummary:
    """Get progress summary for a course."""
    summary = ProgressService.get_course_progress_summary(current_user.id, course_id, db)

    return CourseProgressSummary(**summary)


@router.post(
    "/progress/lessons/{lesson_id}/complete",
    response_model=LessonProgressResponse,
    dependencies=[Depends(RequireLessonEnrollment())],
)
async def mark_lesson_complete(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonProgressResponse:
    """Manually mark a lesson as complete."""
    progress = ProgressService.mark_lesson_complete(current_user.id, lesson_id, db)

    return LessonProgressResponse(
        id=str(progress.id),
        user_id=str(progress.user_id),
        lesson_id=str(progress.lesson_id),
        watched_seconds=progress.watched_seconds,
        last_position_seconds=progress.last_position_seconds,
        completion_percentage=progress.completion_percentage,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
        last_updated_at=progress.last_updated_at,
    )
