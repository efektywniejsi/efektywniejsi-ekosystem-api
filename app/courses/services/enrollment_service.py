from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.courses.models import Course, Enrollment
from app.courses.schemas.course import EnrollmentWithCourseResponse


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

    @staticmethod
    def _map_course_to_enrollment_response(
        course: Course, user_id: UUID
    ) -> EnrollmentWithCourseResponse:
        """Map a Course object to EnrollmentWithCourseResponse (for admin access)."""
        return EnrollmentWithCourseResponse(
            id=str(course.id),
            user_id=str(user_id),
            course_id=str(course.id),
            enrolled_at=datetime.utcnow(),
            completed_at=None,
            certificate_issued_at=None,
            last_accessed_at=None,
            course={
                "id": str(course.id),
                "title": course.title,
                "slug": course.slug,
                "description": course.description,
                "thumbnail_url": course.thumbnail_url,
                "difficulty": course.difficulty,
                "estimated_hours": course.estimated_hours,
                "is_published": course.is_published,
                "category": course.category,
                "sort_order": course.sort_order,
                "created_at": course.created_at,
                "updated_at": course.updated_at,
            },
        )

    @staticmethod
    def _map_enrollment_to_response(enrollment: Enrollment) -> EnrollmentWithCourseResponse:
        """Map an Enrollment object to EnrollmentWithCourseResponse."""
        return EnrollmentWithCourseResponse(
            id=str(enrollment.id),
            user_id=str(enrollment.user_id),
            course_id=str(enrollment.course_id),
            enrolled_at=enrollment.enrolled_at,
            completed_at=enrollment.completed_at,
            certificate_issued_at=enrollment.certificate_issued_at,
            last_accessed_at=enrollment.last_accessed_at,
            course={
                "id": str(enrollment.course.id),
                "title": enrollment.course.title,
                "slug": enrollment.course.slug,
                "description": enrollment.course.description,
                "thumbnail_url": enrollment.course.thumbnail_url,
                "difficulty": enrollment.course.difficulty,
                "estimated_hours": enrollment.course.estimated_hours,
                "is_published": enrollment.course.is_published,
                "category": enrollment.course.category,
                "sort_order": enrollment.course.sort_order,
                "created_at": enrollment.course.created_at,
                "updated_at": enrollment.course.updated_at,
            },
        )

    @staticmethod
    def get_user_accessible_courses(
        user_id: UUID, is_admin: bool, db: Session
    ) -> list[EnrollmentWithCourseResponse]:
        """
        Get courses accessible to a user.
        - Admins see all published courses
        - Regular users see only enrolled published courses
        """
        if is_admin:
            courses = db.query(Course).order_by(Course.sort_order, Course.created_at.desc()).all()
            return [
                EnrollmentService._map_course_to_enrollment_response(course, user_id)
                for course in courses
            ]

        enrollments = (
            db.query(Enrollment)
            .options(joinedload(Enrollment.course))
            .join(Course, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == user_id, Course.is_published == True)  # noqa: E712
            .all()
        )
        return [
            EnrollmentService._map_enrollment_to_response(enrollment) for enrollment in enrollments
        ]
