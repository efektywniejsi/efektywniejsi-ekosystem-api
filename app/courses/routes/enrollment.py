from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
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
    """
    Get all courses accessible to the current user.
    - Admins see all courses automatically (no enrollment required)
    - Regular users see only their enrolled courses
    """
    return EnrollmentService.get_user_accessible_courses(
        user_id=current_user.id,
        is_admin=current_user.role == "admin",
        db=db,
    )
