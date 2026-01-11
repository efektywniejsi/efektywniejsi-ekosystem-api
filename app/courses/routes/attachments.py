import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.courses.models import Attachment, Course, Lesson, Module
from app.courses.services.enrollment_service import EnrollmentService
from app.db.session import get_db

router = APIRouter()

# Allowed MIME types
ALLOWED_MIME_TYPES = ["application/pdf"]


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
    """Upload a PDF attachment to a lesson (admin only)."""
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only PDF files are allowed. Received: {file.content_type}",
        )

    # Check file size
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Generate unique filename
    file_extension = Path(file.filename or "file.pdf").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR) / "attachments"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Create attachment record
    attachment = Attachment(
        lesson_id=lesson_id,
        title=title,
        file_name=file.filename or unique_filename,
        file_path=str(file_path),
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
    # Check if lesson exists
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
) -> FileResponse:
    """Download an attachment (requires enrollment in the course)."""
    # Get attachment
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    # Get lesson -> module -> course
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

    # Check if lesson is preview (no enrollment required)
    if not lesson.is_preview:
        # Check enrollment
        is_enrolled = EnrollmentService.check_enrollment(current_user.id, course.id, db)

        if not is_enrolled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this course to download this attachment",
            )

    # Check if file exists
    if not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server",
        )

    # Return file
    return FileResponse(
        path=attachment.file_path,
        media_type=attachment.mime_type,
        filename=attachment.file_name,
        headers={"Content-Disposition": f'attachment; filename="{attachment.file_name}"'},
    )


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

    # Delete file from filesystem
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    # Delete database record
    db.delete(attachment)
    db.commit()
