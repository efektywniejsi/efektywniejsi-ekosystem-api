"""Integration images API endpoints for custom integration logos/images."""

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
from app.db.session import get_db
from app.integrations.models import Integration

router = APIRouter()

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"}
ALLOWED_IMGHDR_TYPES = {"png", "jpeg", "gif", "webp"}  # SVG checked separately
MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB (smaller for icons/logos)

MIME_TO_EXTENSION = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}

STORAGE_FOLDER = "integration-images"
AUTH_GUIDE_STORAGE_FOLDER = "integration-auth-guide-images"
AUTH_GUIDE_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB for markdown images


@router.post("/integrations/{integration_id}/image")
async def upload_integration_image(
    integration_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload a custom image/logo for an integration (admin only)."""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PNG, JPG, WebP, GIF, SVG. "
            f"Got: {file.content_type}",
        )

    file_content = await file.read()
    if len(file_content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed size of 2MB",
        )

    # Validate actual file content (magic bytes) - skip for SVG (text-based)
    if file.content_type != "image/svg+xml":
        actual_type = imghdr.what(None, h=file_content)
        if actual_type not in ALLOWED_IMGHDR_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a valid image format",
            )

    # Use extension derived from validated MIME type
    file_extension = MIME_TO_EXTENSION.get(file.content_type, ".png")
    unique_filename = f"{uuid_lib.uuid4()}{file_extension}"

    # Use storage abstraction for R2/local compatibility
    storage = get_storage()
    storage.upload(file_content, STORAGE_FOLDER, unique_filename)

    # Return API endpoint URL
    image_url = f"{settings.API_V1_PREFIX}/integrations/{integration_id}/image/{unique_filename}"

    # Update the integration with the new image_url
    integration.image_url = image_url
    db.commit()

    return {"image_url": image_url}


@router.get("/integrations/{integration_id}/image/{filename}")
async def serve_integration_image(
    integration_id: UUID,
    filename: str,
) -> Response:
    """Serve an integration image. Uses redirect for R2, direct serve for local storage."""
    import os
    from pathlib import Path

    # Security: validate filename (no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
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
            detail="Invalid filename",
        )

    # Determine media type from extension
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(path=str(file_path), media_type=media_type)


@router.delete("/integrations/{integration_id}/image")
async def delete_integration_image(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Delete the custom image for an integration (admin only)."""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    if not integration.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration has no custom image",
        )

    # Extract filename from URL and delete from storage
    filename = integration.image_url.split("/")[-1]
    storage = get_storage()
    storage_path = f"{STORAGE_FOLDER}/{filename}"

    if storage.exists(storage_path):
        storage.delete(storage_path)

    # Clear the image_url
    integration.image_url = None
    db.commit()

    return {"message": "Image deleted successfully"}


# ─────────────────────────────────────────────────────────────
# Auth Guide Markdown Images
# ─────────────────────────────────────────────────────────────


@router.post("/integrations/{integration_id}/auth-guide-images")
async def upload_auth_guide_image(
    integration_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an image for use in integration auth guide markdown (admin only)."""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    # Allow standard image types (no SVG for markdown content)
    allowed_types = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PNG, JPG, WebP, GIF. Got: {file.content_type}",
        )

    file_content = await file.read()
    if len(file_content) > AUTH_GUIDE_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed size of 5MB",
        )

    # Validate actual file content (magic bytes)
    actual_type = imghdr.what(None, h=file_content)
    if actual_type not in ALLOWED_IMGHDR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match a valid image format",
        )

    # Use extension derived from validated MIME type
    file_extension = MIME_TO_EXTENSION.get(file.content_type, ".jpg")
    unique_filename = f"{uuid_lib.uuid4()}{file_extension}"

    # Use storage abstraction for R2/local compatibility
    storage = get_storage()
    storage.upload(file_content, AUTH_GUIDE_STORAGE_FOLDER, unique_filename)

    # Return API endpoint URL (works with frontend proxy)
    image_url = (
        f"{settings.API_V1_PREFIX}/integrations/{integration_id}"
        f"/auth-guide-images/{unique_filename}"
    )

    return {"image_url": image_url}


@router.get("/integrations/{integration_id}/auth-guide-images/{filename}")
async def serve_auth_guide_image(
    integration_id: UUID,
    filename: str,
) -> Response:
    """Serve an auth guide image. Uses redirect for R2, direct serve for local."""
    import os
    from pathlib import Path

    # Security: validate filename (no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    storage = get_storage()
    storage_path = f"{AUTH_GUIDE_STORAGE_FOLDER}/{filename}"

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
            detail="Invalid filename",
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
