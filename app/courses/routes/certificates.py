import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.courses.models import Certificate, Course
from app.courses.schemas.certificate import (
    CertificateVerifyResponse,
    CertificateWithCourseResponse,
)
from app.courses.services.certificate_service import CertificateService
from app.db.session import get_db

router = APIRouter()


@router.post(
    "/certificates/courses/{course_id}",
    response_model=CertificateWithCourseResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_certificate(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CertificateWithCourseResponse:
    """Generate a certificate for a completed course."""
    certificate = CertificateService.create_certificate(current_user.id, course_id, db)

    course = db.query(Course).filter(Course.id == course_id).first()

    return CertificateWithCourseResponse(
        id=str(certificate.id),
        user_id=str(certificate.user_id),
        course_id=str(certificate.course_id),
        certificate_code=certificate.certificate_code,
        issued_at=certificate.issued_at,
        file_path=certificate.file_path,
        created_at=certificate.created_at,
        course_title=course.title if course else "Unknown",
        course_slug=course.slug if course else "",
        user_name=current_user.name,
    )


@router.get("/certificates/me", response_model=list[CertificateWithCourseResponse])
async def get_my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CertificateWithCourseResponse]:
    """Get all certificates for the current user."""
    certificates = (
        db.query(Certificate)
        .filter(Certificate.user_id == current_user.id)
        .order_by(Certificate.issued_at.desc())
        .all()
    )

    result = []
    for cert in certificates:
        course = db.query(Course).filter(Course.id == cert.course_id).first()
        result.append(
            CertificateWithCourseResponse(
                id=str(cert.id),
                user_id=str(cert.user_id),
                course_id=str(cert.course_id),
                certificate_code=cert.certificate_code,
                issued_at=cert.issued_at,
                file_path=cert.file_path,
                created_at=cert.created_at,
                course_title=course.title if course else "Unknown",
                course_slug=course.slug if course else "",
                user_name=current_user.name,
            )
        )

    return result


@router.get("/certificates/{certificate_code}/download")
async def download_certificate(
    certificate_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download a certificate PDF."""
    certificate = (
        db.query(Certificate).filter(Certificate.certificate_code == certificate_code).first()
    )

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    if certificate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to download this certificate",
        )

    if not certificate.file_path or not os.path.exists(certificate.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found on server",
        )

    course = db.query(Course).filter(Course.id == certificate.course_id).first()
    filename = (
        f"certificate_{course.slug}_{certificate_code[:8]}.pdf"
        if course
        else f"certificate_{certificate_code[:8]}.pdf"
    )

    return FileResponse(
        path=certificate.file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/certificates/{certificate_code}/verify",
    response_model=CertificateVerifyResponse,
)
async def verify_certificate(
    certificate_code: str,
    db: Session = Depends(get_db),
) -> CertificateVerifyResponse:
    """Verify a certificate by its code (public endpoint)."""
    verification_result = CertificateService.verify_certificate(certificate_code, db)

    return CertificateVerifyResponse(
        valid=verification_result["valid"],
        certificate_code=verification_result["certificate_code"],
        user_name=verification_result["user_name"],
        course_title=verification_result["course_title"],
        issued_at=verification_result["issued_at"],
        message=verification_result["message"],
    )
