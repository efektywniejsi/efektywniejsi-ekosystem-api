"""
Package enrollment API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.db.session import get_db
from app.packages.models.enrollment import PackageEnrollment
from app.packages.schemas.enrollment import PackageEnrollmentResponse

router = APIRouter(prefix="/package-enrollments", tags=["enrollments"])


@router.get("/me", response_model=list[PackageEnrollmentResponse])
def get_my_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PackageEnrollmentResponse]:
    """
    Get current user's package enrollments.

    Returns:
        List of user's package enrollments with package details

    Requires:
        Authentication (current user from token)
    """
    enrollments = (
        db.query(PackageEnrollment)
        .filter(PackageEnrollment.user_id == current_user.id)
        .order_by(PackageEnrollment.enrolled_at.desc())
        .all()
    )

    return [
        PackageEnrollmentResponse(
            id=enrollment.id,
            package_id=enrollment.package_id,
            enrolled_at=enrollment.enrolled_at,
            last_accessed_at=enrollment.last_accessed_at,
            package={
                "id": enrollment.package.id,
                "slug": enrollment.package.slug,
                "title": enrollment.package.title,
                "description": enrollment.package.description,
                "category": enrollment.package.category,
                "difficulty": enrollment.package.difficulty,
                "total_time_saved": enrollment.package.total_time_saved,
            },
        )
        for enrollment in enrollments
    ]


@router.get("/{package_id}/check")
def check_enrollment(
    package_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """
    Check if current user is enrolled in a specific package.

    Args:
        package_id: Package UUID

    Returns:
        {"is_enrolled": true/false}

    Requires:
        Authentication
    """
    import uuid

    try:
        package_uuid = uuid.UUID(package_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid package ID format")

    enrollment = (
        db.query(PackageEnrollment)
        .filter(
            PackageEnrollment.user_id == current_user.id,
            PackageEnrollment.package_id == package_uuid,
        )
        .first()
    )

    return {"is_enrolled": enrollment is not None}
