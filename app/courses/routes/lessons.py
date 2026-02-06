from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.dependencies import RequireCourseEnrollment, RequireLessonEnrollment
from app.courses.models import Course, Lesson, LessonProgress, Module
from app.courses.schemas.course import LessonResponse, LessonWithProgressResponse
from app.courses.services.enrollment_service import EnrollmentService
from app.db.session import get_db

router = APIRouter()


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonWithProgressResponse,
    dependencies=[Depends(RequireLessonEnrollment())],
)
async def get_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonWithProgressResponse:
    """Get lesson details with user progress."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    progress = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == current_user.id, LessonProgress.lesson_id == lesson_id)
        .first()
    )

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    if module:
        EnrollmentService.update_last_accessed(current_user.id, module.course_id, db)

    return LessonWithProgressResponse(
        id=str(lesson.id),
        module_id=str(lesson.module_id),
        title=lesson.title,
        description=lesson.description,
        mux_playback_id=lesson.mux_playback_id,
        mux_asset_id=lesson.mux_asset_id,
        duration_seconds=lesson.duration_seconds,
        sort_order=lesson.sort_order,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
        watched_seconds=progress.watched_seconds if progress else 0,
        last_position_seconds=progress.last_position_seconds if progress else 0,
        completion_percentage=progress.completion_percentage if progress else 0,
        is_completed=progress.is_completed if progress else False,
    )


@router.get("/courses/{slug}/lessons", response_model=list[LessonResponse])
async def get_course_lessons(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LessonResponse]:
    """Get all lessons for a course (requires enrollment)."""
    course = db.query(Course).filter(Course.slug == slug).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    RequireCourseEnrollment()(course_id=course.id, current_user=current_user, db=db)

    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course.id)
        .order_by(Module.sort_order, Lesson.sort_order)
        .all()
    )

    return [
        LessonResponse(
            id=str(lesson.id),
            module_id=str(lesson.module_id),
            title=lesson.title,
            description=lesson.description,
            mux_playback_id=lesson.mux_playback_id,
            mux_asset_id=lesson.mux_asset_id,
            duration_seconds=lesson.duration_seconds,
            sort_order=lesson.sort_order,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )
        for lesson in lessons
    ]
