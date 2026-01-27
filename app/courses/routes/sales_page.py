"""Sales page builder API endpoints."""

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
from app.courses.services.sales_page_service import get_sales_page, update_sales_page
from app.db.session import get_db

router = APIRouter()


@router.get(
    "/courses/{course_id}/sales-page",
    response_model=SalesPageResponse,
)
async def get_course_sales_page(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Get sales page configuration for a course (admin only)."""
    data = get_sales_page(db, course_id)
    if data is not None:
        return SalesPageResponse(sales_page_sections=SalesPageData.model_validate(data))
    return SalesPageResponse(sales_page_sections=None)


@router.put(
    "/courses/{course_id}/sales-page",
    response_model=SalesPageResponse,
)
async def update_course_sales_page(
    course_id: UUID,
    request: SalesPageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Update sales page configuration for a course (admin only)."""
    result = update_sales_page(db, course_id, request.sales_page_sections)
    return SalesPageResponse(sales_page_sections=SalesPageData.model_validate(result))


ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"]


@router.post("/courses/{course_id}/sales-page/upload-image")
async def upload_sales_page_image(
    course_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an image for a sales page section (admin only)."""
    from app.courses.models.course import Course

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
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
            detail="File size exceeds maximum allowed size of 5MB",
        )

    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid_lib.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "sales-page"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    image_url = f"{settings.API_V1_PREFIX}/courses/{course_id}/sales-page/images/{unique_filename}"

    return {"image_url": image_url}


@router.get("/courses/{course_id}/sales-page/images/{filename}")
async def serve_sales_page_image(
    course_id: UUID,
    filename: str,
) -> FileResponse:
    """Serve a sales page image."""
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
