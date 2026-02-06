from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.core.storage import generate_unique_filename, get_storage
from app.courses.models import Attachment, Course, Lesson, Module
from app.courses.services.enrollment_service import EnrollmentService
from app.db.session import get_db

router = APIRouter()

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/zip",
    "image/png",
    "image/jpeg",
]


@router.post(
    "/lessons/{lesson_id}/attachments",
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    lesson_id: UUID,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an attachment to a lesson (admin only).

    Supports PDF, DOCX, ZIP, PNG, JPG files up to 50MB.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file type. Allowed types: PDF, DOCX, ZIP, PNG, JPG. "
                f"Received: {file.content_type}"
            ),
        )

    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    unique_filename = generate_unique_filename(file.filename or "file.pdf")
    storage = get_storage()
    stored_path = storage.upload(file_content, "attachments", unique_filename)

    attachment = Attachment(
        lesson_id=lesson_id,
        title=title,
        file_name=file.filename or unique_filename,
        file_path=stored_path,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/pdf",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": str(attachment.id),
        "lesson_id": str(attachment.lesson_id),
        "title": attachment.title,
        "file_name": attachment.file_name,
        "file_size_bytes": attachment.file_size_bytes,
        "mime_type": attachment.mime_type,
        "created_at": attachment.created_at,
    }


@router.get("/lessons/{lesson_id}/attachments")
async def list_lesson_attachments(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List all attachments for a lesson."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    attachments = (
        db.query(Attachment)
        .filter(Attachment.lesson_id == lesson_id)
        .order_by(Attachment.sort_order, Attachment.created_at)
        .all()
    )

    return [
        {
            "id": str(a.id),
            "lesson_id": str(a.lesson_id),
            "title": a.title,
            "file_name": a.file_name,
            "file_size_bytes": a.file_size_bytes,
            "mime_type": a.mime_type,
            "sort_order": a.sort_order,
            "created_at": a.created_at,
        }
        for a in attachments
    ]


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    """Download an attachment (requires enrollment in the course)."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    lesson = db.query(Lesson).filter(Lesson.id == attachment.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
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

    is_enrolled = EnrollmentService.check_enrollment(current_user.id, course.id, db)

    if not is_enrolled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this course to download this attachment",
        )

    storage = get_storage()
    if not storage.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server",
        )

    url = storage.download_url(attachment.file_path)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Delete an attachment (admin only)."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    storage = get_storage()
    storage.delete(attachment.file_path)

    db.delete(attachment)
    db.commit()
