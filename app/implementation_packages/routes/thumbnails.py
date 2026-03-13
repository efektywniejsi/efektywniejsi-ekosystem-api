"""Routes for implementation package thumbnail uploads."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.core.constants import THUMBNAIL_ALLOWED_MIME_TYPES, THUMBNAIL_MAX_SIZE_BYTES
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import ImplementationPackage

router = APIRouter()


@router.post("/{package_id}/learning-thumbnail")
@limiter.limit("30/minute")
async def upload_package_learning_thumbnail(
    request: Request,
    package_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload a learning thumbnail image for an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
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
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "thumbnails"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Remove old thumbnail file if it exists
    if pkg.learning_thumbnail_url:
        old_path = upload_dir / Path(pkg.learning_thumbnail_url).name
        if old_path.exists():
            old_path.unlink()

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    thumbnail_url = (
        f"{settings.API_V1_PREFIX}/implementation-packages/{package_id}"
        f"/learning-thumbnail/{unique_filename}"
    )
    pkg.learning_thumbnail_url = thumbnail_url

    db.commit()
    db.refresh(pkg)

    return {
        "learning_thumbnail_url": thumbnail_url,
    }


@router.get("/{package_id}/learning-thumbnail/{filename}")
async def serve_package_learning_thumbnail(
    package_id: uuid.UUID,
    filename: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Serve a learning thumbnail image for an implementation package."""
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
