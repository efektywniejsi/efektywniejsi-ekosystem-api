from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.courses.models import Course, Enrollment


class EnrollmentService:
    @staticmethod
    def enroll_user(user_id: UUID, course_id: UUID, db: Session) -> Enrollment:
        """Enroll a user in a course."""
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        if not course.is_published:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Course is not published",
            )

        existing_enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )

        if existing_enrollment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already enrolled in this course",
            )

        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            enrolled_at=datetime.utcnow(),
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)

        return cast(Enrollment, enrollment)

    @staticmethod
    def unenroll_user(user_id: UUID, course_id: UUID, db: Session) -> None:
        """Unenroll a user from a course."""
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        db.delete(enrollment)
        db.commit()

    @staticmethod
    def check_enrollment(user_id: UUID, course_id: UUID, db: Session) -> bool:
        """Check if a user is enrolled in a course."""
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )
        return enrollment is not None

    @staticmethod
    def get_user_enrollment(user_id: UUID, course_id: UUID, db: Session) -> Enrollment | None:
        """Get user's enrollment for a specific course."""
        result = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )
        return cast(Enrollment | None, result)

    @staticmethod
    def update_last_accessed(user_id: UUID, course_id: UUID, db: Session) -> None:
        """Update last accessed timestamp for an enrollment."""
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )

        if enrollment:
            enrollment.last_accessed_at = datetime.utcnow()
            db.commit()
