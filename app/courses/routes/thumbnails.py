"""Course thumbnail management routes (admin only)."""

import os
import uuid as uuid_lib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.core.constants import THUMBNAIL_ALLOWED_MIME_TYPES, THUMBNAIL_MAX_SIZE_BYTES
from app.courses.models import Course
from app.db.session import get_db

router = APIRouter()


@router.post("/courses/{course_id}/learning-thumbnail")
async def upload_learning_thumbnail(
    course_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload a learning thumbnail image for a course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    if file.content_type not in THUMBNAIL_ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieprawidłowy typ pliku. Dozwolone: PNG, JPG, WebP. "
            f"Otrzymano: {file.content_type}",
        )

    file_content = await file.read()
    if len(file_content) > THUMBNAIL_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Rozmiar pliku przekracza maksymalny dozwolony rozmiar 5MB",
        )

    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid_lib.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "thumbnails"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Remove old thumbnail file if it exists
    if course.learning_thumbnail_url:
        old_path = upload_dir / Path(course.learning_thumbnail_url).name
        if old_path.exists():
            os.remove(old_path)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    thumbnail_url = (
        f"{settings.API_V1_PREFIX}/courses/{course_id}/learning-thumbnail/{unique_filename}"
    )
    course.learning_thumbnail_url = thumbnail_url

    db.commit()
    db.refresh(course)

    return {
        "learning_thumbnail_url": thumbnail_url,
    }


@router.get("/courses/{course_id}/learning-thumbnail/{filename}")
async def serve_learning_thumbnail(
    course_id: UUID,
    filename: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Serve a learning thumbnail image."""
    upload_root = (Path(settings.UPLOAD_DIR) / "thumbnails").resolve()
    file_path = (upload_root / filename).resolve()

    # Security check: prevent path traversal
    if not str(file_path).startswith(str(upload_root)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa nazwa pliku",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Miniaturka nie znaleziona",
        )

    media_type = "image/jpeg"
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=str(file_path), media_type=media_type)
