"""Routes for implementation package sales pages."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.config import settings
from app.core.rate_limit import limiter
from app.courses.schemas.sales_page import (
    SECTION_CONFIG_MAP,
    SalesPageData,
    SalesPageResponse,
    SalesPageUpdateRequest,
)
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import ImplementationPackage

SALES_PAGE_ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"]

router = APIRouter()


@router.get(
    "/{package_id}/sales-page",
    response_model=SalesPageResponse,
)
@limiter.limit("60/minute")
async def get_impl_package_sales_page(
    request: Request,
    package_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Get sales page configuration for an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    if pkg.sales_page_sections is not None:
        return SalesPageResponse(
            sales_page_sections=SalesPageData.model_validate(pkg.sales_page_sections)
        )
    return SalesPageResponse(sales_page_sections=None)


@router.put(
    "/{package_id}/sales-page",
    response_model=SalesPageResponse,
)
@limiter.limit("30/minute")
async def update_impl_package_sales_page(
    request: Request,
    package_id: uuid.UUID,
    payload: SalesPageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Update sales page configuration for an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    for section in payload.sales_page_sections.sections:
        config_cls = SECTION_CONFIG_MAP.get(section.type)
        if config_cls:
            try:
                config_cls.model_validate(section.config)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Nieprawidłowa konfiguracja sekcji '{section.type}' (id={section.id}): {e}"
                    ),
                ) from e

    pkg.sales_page_sections = payload.sales_page_sections.model_dump()
    db.commit()
    db.refresh(pkg)

    return SalesPageResponse(
        sales_page_sections=SalesPageData.model_validate(pkg.sales_page_sections)
    )


@router.post("/{package_id}/sales-page/upload-image")
@limiter.limit("30/minute")
async def upload_impl_package_sales_page_image(
    request: Request,
    package_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an image for an implementation package sales page section (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    if file.content_type not in SALES_PAGE_ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nieprawidłowy typ pliku. Dozwolone: PNG, JPG, WebP."
                f" Otrzymano: {file.content_type}"
            ),
        )

    max_size_bytes = 5 * 1024 * 1024  # 5 MB
    file_content = await file.read()
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Rozmiar pliku przekracza maksymalny dozwolony rozmiar 5MB",
        )

    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "sales-page"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    image_url = (
        f"{settings.API_V1_PREFIX}/implementation-packages/{package_id}"
        f"/sales-page/images/{unique_filename}"
    )

    return {"image_url": image_url}


@router.get("/{package_id}/sales-page/images/{filename}")
async def serve_impl_package_sales_page_image(
    package_id: uuid.UUID,
    filename: str,
) -> FileResponse:
    """Serve an implementation package sales page image."""
    upload_root = (Path(settings.UPLOAD_DIR) / "sales-page").resolve()
    file_path = (upload_root / filename).resolve()

    if not str(file_path).startswith(str(upload_root)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa nazwa pliku",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Obraz nie znaleziony",
        )

    media_type = "image/jpeg"
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=str(file_path), media_type=media_type)
