"""Bundle sales page builder API endpoints."""

import uuid as uuid_lib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.courses.schemas.sales_page import (
    SalesPageData,
    SalesPageResponse,
    SalesPageUpdateRequest,
)
from app.db.session import get_db
from app.packages.services.bundle_sales_page_service import (
    get_bundle_sales_page,
    update_bundle_sales_page,
)

router = APIRouter()


@router.get(
    "/bundles/{bundle_id}/sales-page",
    response_model=SalesPageResponse,
)
async def get_bundle_sales_page_endpoint(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Get sales page configuration for a bundle (admin only)."""
    data = get_bundle_sales_page(db, bundle_id)
    if data is not None:
        return SalesPageResponse(sales_page_sections=SalesPageData.model_validate(data))
    return SalesPageResponse(sales_page_sections=None)


@router.put(
    "/bundles/{bundle_id}/sales-page",
    response_model=SalesPageResponse,
)
async def update_bundle_sales_page_endpoint(
    bundle_id: UUID,
    request: SalesPageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Update sales page configuration for a bundle (admin only)."""
    result = update_bundle_sales_page(db, bundle_id, request.sales_page_sections)
    return SalesPageResponse(sales_page_sections=SalesPageData.model_validate(result))


ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"]


@router.post("/bundles/{bundle_id}/sales-page/upload-image")
async def upload_bundle_sales_page_image(
    bundle_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an image for a bundle sales page section (admin only)."""
    from app.packages.models.package import Package

    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_id, Package.is_bundle == True)  # noqa: E712
        .first()
    )
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PNG, JPG, WebP. Received: {file.content_type}",
        )

    max_size_bytes = 5 * 1024 * 1024  # 5 MB
    file_content = await file.read()
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Rozmiar pliku przekracza maksymalny dozwolony rozmiar 5MB",
        )

    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid_lib.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "sales-page"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    image_url = f"{settings.API_V1_PREFIX}/bundles/{bundle_id}/sales-page/images/{unique_filename}"

    return {"image_url": image_url}


@router.get("/bundles/{bundle_id}/sales-page/images/{filename}")
async def serve_bundle_sales_page_image(
    bundle_id: UUID,
    filename: str,
) -> FileResponse:
    """Serve a bundle sales page image."""
    file_path = Path(settings.UPLOAD_DIR) / "sales-page" / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    media_type = "image/jpeg"
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=str(file_path), media_type=media_type)
