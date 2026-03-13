"""Routes for implementation package enrollments."""

import secrets
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.auth.services.email_service import build_welcome_email, get_email_service
from app.core import security
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import (
    ImplementationPackage,
    ImplementationPackageEnrollment,
)
from app.implementation_packages.schemas import (
    ImplPackageEnrollmentCreateRequest,
    ImplPackageEnrollmentListResponse,
    ImplPackageEnrollmentResponse,
    ImplPackageEnrollmentUpdateRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


def _enrollment_to_response(
    enrollment: ImplementationPackageEnrollment,
) -> ImplPackageEnrollmentResponse:
    return ImplPackageEnrollmentResponse(
        id=str(enrollment.id),
        user_id=str(enrollment.user_id),
        package_id=str(enrollment.package_id),
        user_name=enrollment.user.name if enrollment.user else None,
        user_email=enrollment.user.email if enrollment.user else "",
        enrolled_at=enrollment.enrolled_at,
        expires_at=enrollment.expires_at,
        is_expired=enrollment.is_expired,
    )


@router.get(
    "/{package_id}/enrollments",
    response_model=ImplPackageEnrollmentListResponse,
)
@limiter.limit("60/minute")
async def list_package_enrollments(
    request: Request,
    package_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageEnrollmentListResponse:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    query = (
        db.query(ImplementationPackageEnrollment)
        .options(joinedload(ImplementationPackageEnrollment.user))
        .filter(ImplementationPackageEnrollment.package_id == package_id)
    )
    total = (
        db.query(ImplementationPackageEnrollment)
        .filter(ImplementationPackageEnrollment.package_id == package_id)
        .count()
    )
    enrollments = query.offset(skip).limit(limit).all()

    return ImplPackageEnrollmentListResponse(
        total=total,
        enrollments=[_enrollment_to_response(e) for e in enrollments],
    )


@router.post(
    "/{package_id}/enrollments",
    response_model=ImplPackageEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_package_enrollment(
    request: Request,
    package_id: uuid.UUID,
    data: ImplPackageEnrollmentCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageEnrollmentResponse:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    user = db.query(User).filter(User.email == data.email).first()
    send_welcome = False
    temp_password = ""

    if not user:
        temp_password = secrets.token_urlsafe(12)
        user = User(
            email=data.email,
            name=data.name or data.email.split("@")[0],
            hashed_password=security.get_password_hash(temp_password),
            role="paid",
            is_active=True,
        )
        db.add(user)
        db.flush()
        send_welcome = True

    existing = (
        db.query(ImplementationPackageEnrollment)
        .filter(
            ImplementationPackageEnrollment.user_id == user.id,
            ImplementationPackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Użytkownik jest już zapisany do tego pakietu",
        )

    enrollment = ImplementationPackageEnrollment(
        user_id=user.id,
        package_id=package_id,
        enrolled_at=datetime.now(UTC),
        expires_at=data.expires_at,
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
            logger.warning("Could not send welcome email: %s", e)

    return _enrollment_to_response(enrollment)


@router.patch(
    "/{package_id}/enrollments/{enrollment_id}",
    response_model=ImplPackageEnrollmentResponse,
)
@limiter.limit("30/minute")
async def update_package_enrollment(
    request: Request,
    package_id: uuid.UUID,
    enrollment_id: uuid.UUID,
    data: ImplPackageEnrollmentUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageEnrollmentResponse:
    enrollment = (
        db.query(ImplementationPackageEnrollment)
        .options(joinedload(ImplementationPackageEnrollment.user))
        .filter(
            ImplementationPackageEnrollment.id == enrollment_id,
            ImplementationPackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zapis nie znaleziony")

    enrollment.expires_at = data.expires_at
    db.commit()
    db.refresh(enrollment)

    return _enrollment_to_response(enrollment)


@router.delete(
    "/{package_id}/enrollments/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def delete_package_enrollment(
    request: Request,
    package_id: uuid.UUID,
    enrollment_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    enrollment = (
        db.query(ImplementationPackageEnrollment)
        .filter(
            ImplementationPackageEnrollment.id == enrollment_id,
            ImplementationPackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zapis nie znaleziony")

    db.delete(enrollment)
    db.commit()
