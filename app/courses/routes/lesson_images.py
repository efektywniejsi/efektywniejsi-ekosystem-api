"""Lesson images API endpoints for inline markdown images."""

import imghdr
import uuid as uuid_lib
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.core.storage import get_storage
from app.courses.models import Lesson
from app.db.session import get_db

router = APIRouter()

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
ALLOWED_IMGHDR_TYPES = {"png", "jpeg", "gif", "webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Map validated MIME types to safe extensions (prevents extension spoofing)
MIME_TO_EXTENSION = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

STORAGE_FOLDER = "lesson-images"


@router.post("/lessons/{lesson_id}/images")
async def upload_lesson_image(
    lesson_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an image for use in lesson markdown description (admin only)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PNG, JPG, WebP, GIF. Got: {file.content_type}",
        )

    file_content = await file.read()
    if len(file_content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Rozmiar pliku przekracza maksymalny dozwolony rozmiar 5MB",
        )

    # Validate actual file content (magic bytes) to prevent spoofed Content-Type
    actual_type = imghdr.what(None, h=file_content)
    if actual_type not in ALLOWED_IMGHDR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zawartość pliku nie odpowiada prawidłowemu formatowi obrazu",
        )

    # Use extension derived from validated MIME type (not user-provided filename)
    file_extension = MIME_TO_EXTENSION.get(file.content_type, ".jpg")
    unique_filename = f"{uuid_lib.uuid4()}{file_extension}"

    # Use storage abstraction for R2/local compatibility
    storage = get_storage()
    storage.upload(file_content, STORAGE_FOLDER, unique_filename)

    # Return API endpoint URL (works with frontend proxy, like sales_page.py pattern)
    image_url = f"{settings.API_V1_PREFIX}/lessons/{lesson_id}/images/{unique_filename}"

    return {"image_url": image_url}


@router.get("/lessons/{lesson_id}/images/{filename}")
async def serve_lesson_image(
    lesson_id: UUID,
    filename: str,
) -> Response:
    """Serve a lesson image. Uses redirect for R2, direct serve for local storage."""
    import os
    from pathlib import Path

    # Security: validate filename (no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa nazwa pliku",
        )

    storage = get_storage()
    storage_path = f"{STORAGE_FOLDER}/{filename}"

    if not storage.exists(storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # For R2 storage: redirect to public URL (CDN-served)
    if settings.STORAGE_BACKEND == "r2":
        download_url = storage.download_url(storage_path)
        return RedirectResponse(url=download_url, status_code=status.HTTP_302_FOUND)

    # For local storage: serve file directly
    file_path = Path(settings.UPLOAD_DIR) / storage_path
    file_path = file_path.resolve()

    # Ensure path is within upload directory
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    if not str(file_path).startswith(str(upload_root) + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa nazwa pliku",
        )

    # Determine media type from extension
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(path=str(file_path), media_type=media_type)
