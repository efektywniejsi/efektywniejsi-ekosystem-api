from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.models import Course, Lesson, LessonStatus, Module
from app.courses.services.enrollment_service import EnrollmentService
from app.db.session import get_db


def require_course_enrollment(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Dependency to check if user is enrolled in a course."""
    is_enrolled = EnrollmentService.check_enrollment(current_user.id, course_id, db)

    if not is_enrolled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this course to access it",
        )


def require_lesson_enrollment(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Dependency to check if user is enrolled in the course containing this lesson."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    # Check lesson status for non-admin users
    if current_user.role != "admin":
        if lesson.status == LessonStatus.UNAVAILABLE:
            # Pretend the lesson doesn't exist for non-admins
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )
        if lesson.status == LessonStatus.IN_PREPARATION:
            # Lesson exists but is not accessible
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This lesson is currently in preparation and not yet available",
            )

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found",
        )

    course = db.query(Course).filter(Course.id == module.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if lesson.is_preview:
        return

    is_enrolled = EnrollmentService.check_enrollment(current_user.id, course.id, db)

    if not is_enrolled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this course to access this lesson",
        )
