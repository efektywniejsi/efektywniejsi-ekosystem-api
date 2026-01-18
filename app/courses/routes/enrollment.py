from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.models import Enrollment
from app.courses.schemas.course import EnrollmentResponse, EnrollmentWithCourseResponse
from app.courses.services.enrollment_service import EnrollmentService
from app.db.session import get_db

router = APIRouter()


@router.post(
    "/courses/{course_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_200_OK,
)
async def enroll_in_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnrollmentResponse:
    """Enroll current user in a course."""
    enrollment = EnrollmentService.enroll_user(current_user.id, course_id, db)

    return EnrollmentResponse(
        id=str(enrollment.id),
        user_id=str(enrollment.user_id),
        course_id=str(enrollment.course_id),
        enrolled_at=enrollment.enrolled_at,
        completed_at=enrollment.completed_at,
        certificate_issued_at=enrollment.certificate_issued_at,
        last_accessed_at=enrollment.last_accessed_at,
    )


@router.delete("/courses/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
async def unenroll_from_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Unenroll current user from a course."""
    EnrollmentService.unenroll_user(current_user.id, course_id, db)


@router.get("/enrollments/me", response_model=list[EnrollmentWithCourseResponse])
async def get_my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EnrollmentWithCourseResponse]:
    """Get all enrollments for the current user. Admins automatically see all courses."""

    # Admins see all courses automatically (no enrollment required)
    if current_user.role == "admin":
        from datetime import datetime

        from app.courses.models import Course

        courses = db.query(Course).order_by(Course.sort_order, Course.created_at.desc()).all()

        return [
            EnrollmentWithCourseResponse(
                id=str(course.id),  # Use course ID as enrollment ID for admins
                user_id=str(current_user.id),
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
                    "is_featured": course.is_featured,
                    "category": course.category,
                    "sort_order": course.sort_order,
                    "created_at": course.created_at,
                    "updated_at": course.updated_at,
                },
            )
            for course in courses
        ]

    # Regular users see only their enrolled courses
    enrollments = (
        db.query(Enrollment)
        .options(joinedload(Enrollment.course))
        .filter(Enrollment.user_id == current_user.id)
        .all()
    )

    return [
        EnrollmentWithCourseResponse(
            id=str(e.id),
            user_id=str(e.user_id),
            course_id=str(e.course_id),
            enrolled_at=e.enrolled_at,
            completed_at=e.completed_at,
            certificate_issued_at=e.certificate_issued_at,
            last_accessed_at=e.last_accessed_at,
            course={
                "id": str(e.course.id),
                "title": e.course.title,
                "slug": e.course.slug,
                "description": e.course.description,
                "thumbnail_url": e.course.thumbnail_url,
                "difficulty": e.course.difficulty,
                "estimated_hours": e.course.estimated_hours,
                "is_published": e.course.is_published,
                "is_featured": e.course.is_featured,
                "category": e.course.category,
                "sort_order": e.course.sort_order,
                "created_at": e.course.created_at,
                "updated_at": e.course.updated_at,
            },
        )
        for e in enrollments
    ]
