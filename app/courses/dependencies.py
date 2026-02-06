from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.models import Course, Lesson, LessonStatus, Module
from app.courses.services.enrollment_service import EnrollmentService
from app.db.session import get_db


def _is_admin(user: User) -> bool:
    """Check if user has admin role."""
    return bool(user.role == "admin")


class RequireCourseEnrollment:
    """Dependency class to check if user is enrolled in a course."""

    def __init__(self, skip_for_admin: bool = True):
        """
        Initialize enrollment requirement.

        Args:
            skip_for_admin: If True, admins bypass enrollment check. Default True.
        """
        self.skip_for_admin = skip_for_admin

    def __call__(
        self,
        course_id: UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        if self.skip_for_admin and _is_admin(current_user):
            return

        enrollment = EnrollmentService.get_user_enrollment(current_user.id, course_id, db)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this course to access it",
            )
        if enrollment.is_expired:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access to this course has expired",
            )


class RequireLessonEnrollment:
    """Dependency class to check if user is enrolled in the course containing a lesson."""

    def __init__(self, skip_for_admin: bool = True):
        """
        Initialize lesson enrollment requirement.

        Args:
            skip_for_admin: If True, admins bypass enrollment check. Default True.
        """
        self.skip_for_admin = skip_for_admin

    def __call__(
        self,
        lesson_id: UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        if not (self.skip_for_admin and _is_admin(current_user)):
            if lesson.status == LessonStatus.UNAVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson not found",
                )
            if lesson.status == LessonStatus.IN_PREPARATION:
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

        if self.skip_for_admin and _is_admin(current_user):
            return

        enrollment = EnrollmentService.get_user_enrollment(current_user.id, course.id, db)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this course to access this lesson",
            )
        if enrollment.is_expired:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your access to this course has expired",
            )
