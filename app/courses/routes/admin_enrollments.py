import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.auth.services.email_service import build_welcome_email, get_email_service
from app.core import security
from app.courses.models import Course, Enrollment
from app.courses.schemas.enrollment import (
    AdminCreateEnrollmentRequest,
    AdminEnrollmentListResponse,
    AdminEnrollmentResponse,
    AdminUpdateEnrollmentRequest,
)
from app.db.session import get_db

router = APIRouter()


def _enrollment_to_response(enrollment: Enrollment) -> AdminEnrollmentResponse:
    return AdminEnrollmentResponse(
        id=str(enrollment.id),
        user_id=str(enrollment.user_id),
        course_id=str(enrollment.course_id),
        user_name=enrollment.user.name if enrollment.user else None,
        user_email=enrollment.user.email if enrollment.user else "",
        enrolled_at=enrollment.enrolled_at,
        expires_at=enrollment.expires_at,
        is_expired=enrollment.is_expired,
    )


@router.get(
    "/courses/{course_id}/enrollments",
    response_model=AdminEnrollmentListResponse,
)
async def list_course_enrollments(
    course_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminEnrollmentListResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    query = db.query(Enrollment).filter(Enrollment.course_id == course_id)
    total = query.count()
    enrollments = query.offset(skip).limit(limit).all()

    return AdminEnrollmentListResponse(
        total=total,
        enrollments=[_enrollment_to_response(e) for e in enrollments],
    )


@router.post(
    "/courses/{course_id}/enrollments",
    response_model=AdminEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_enrollment(
    course_id: UUID,
    request: AdminCreateEnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminEnrollmentResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    user = db.query(User).filter(User.email == request.email).first()
    send_welcome = False
    temp_password = ""

    if not user:
        temp_password = secrets.token_urlsafe(12)
        user = User(
            email=request.email,
            name=request.name or request.email.split("@")[0],
            hashed_password=security.get_password_hash(temp_password),
            role="paid",
            is_active=True,
        )
        db.add(user)
        db.flush()
        send_welcome = True

    existing = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already enrolled in this course",
        )

    enrollment = Enrollment(
        user_id=user.id,
        course_id=course_id,
        enrolled_at=datetime.utcnow(),
        expires_at=request.expires_at,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    if send_welcome:
        try:
            email_service = get_email_service()
            email_message = build_welcome_email(
                name=str(user.name),
                email=str(user.email),
                temp_password=temp_password,
            )
            await email_service.send_email(email_message)
        except Exception as e:
            print(f"Warning: Could not send welcome email: {e}")

    return _enrollment_to_response(enrollment)


@router.patch(
    "/courses/{course_id}/enrollments/{enrollment_id}",
    response_model=AdminEnrollmentResponse,
)
async def update_enrollment(
    course_id: UUID,
    enrollment_id: UUID,
    request: AdminUpdateEnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminEnrollmentResponse:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    enrollment.expires_at = request.expires_at
    db.commit()
    db.refresh(enrollment)

    return _enrollment_to_response(enrollment)


@router.delete(
    "/courses/{course_id}/enrollments/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_enrollment(
    course_id: UUID,
    enrollment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    db.delete(enrollment)
    db.commit()
