"""Course management routes."""

import logging
import os
import uuid as uuid_lib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_optional_current_user, require_admin
from app.auth.models.user import User
from app.core import security
from app.core.config import settings
from app.courses.models import Course, LessonStatus, Module
from app.courses.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdate,
    DeleteCourseRequest,
    DeleteCourseResponse,
    LessonResponse,
    ModuleWithLessonsResponse,
)
from app.courses.services.mux_service import MuxService, get_mux_service
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

THUMBNAIL_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"]


@router.post(
    "/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_course(
    request: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CourseResponse:
    """Create a new course (admin only)."""
    existing = db.query(Course).filter(Course.slug == request.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kurs z tym slugiem już istnieje",
        )

    course = Course(
        title=request.title,
        slug=request.slug,
        description=request.description,
        thumbnail_url=request.thumbnail_url,
        difficulty=request.difficulty,
        estimated_hours=request.estimated_hours,
        is_published=request.is_published,
        category=request.category,
        sort_order=request.sort_order,
        content_type=request.content_type,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    return CourseResponse(
        id=str(course.id),
        title=course.title,
        slug=course.slug,
        description=course.description,
        thumbnail_url=course.thumbnail_url,
        difficulty=course.difficulty,
        estimated_hours=course.estimated_hours,
        is_published=course.is_published,
        category=course.category,
        sort_order=course.sort_order,
        content_type=course.content_type,
        learning_title=course.learning_title,
        learning_description=course.learning_description,
        learning_thumbnail_url=course.learning_thumbnail_url,
        sales_page_sections=course.sales_page_sections,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    category: str | None = Query(None, description="Filter by category"),
    content_type: str | None = Query(None, description="Filter by content type"),
    db: Session = Depends(get_db),
) -> list[CourseResponse]:
    """List published courses (public endpoint)."""
    query = db.query(Course).filter(Course.is_published == True)  # noqa: E712

    if category:
        query = query.filter(Course.category == category)

    if content_type:
        query = query.filter(Course.content_type == content_type)

    courses = query.order_by(Course.sort_order, Course.created_at).all()

    return [
        CourseResponse(
            id=str(c.id),
            title=c.title,
            slug=c.slug,
            description=c.description,
            thumbnail_url=c.thumbnail_url,
            difficulty=c.difficulty,
            estimated_hours=c.estimated_hours,
            is_published=c.is_published,
            category=c.category,
            sort_order=c.sort_order,
            content_type=c.content_type,
            learning_title=c.learning_title,
            learning_description=c.learning_description,
            learning_thumbnail_url=c.learning_thumbnail_url,
            sales_page_sections=c.sales_page_sections,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in courses
    ]


@router.get("/courses/all", response_model=list[CourseResponse])
async def list_all_courses(
    is_published: bool | None = Query(None, description="Filter by published status"),
    category: str | None = Query(None, description="Filter by category"),
    content_type: str | None = Query(None, description="Filter by content type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[CourseResponse]:
    """List all courses including unpublished (admin only)."""
    query = db.query(Course)

    if is_published is not None:
        query = query.filter(Course.is_published == is_published)

    if category:
        query = query.filter(Course.category == category)

    if content_type:
        query = query.filter(Course.content_type == content_type)

    courses = query.order_by(Course.sort_order, Course.created_at).all()

    return [
        CourseResponse(
            id=str(c.id),
            title=c.title,
            slug=c.slug,
            description=c.description,
            thumbnail_url=c.thumbnail_url,
            difficulty=c.difficulty,
            estimated_hours=c.estimated_hours,
            is_published=c.is_published,
            category=c.category,
            sort_order=c.sort_order,
            content_type=c.content_type,
            learning_title=c.learning_title,
            learning_description=c.learning_description,
            learning_thumbnail_url=c.learning_thumbnail_url,
            sales_page_sections=c.sales_page_sections,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in courses
    ]


@router.get("/courses/{slug}", response_model=CourseDetailResponse)
async def get_course(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> CourseDetailResponse:
    """Get course details. Admins can see unpublished courses and all lessons."""
    is_admin = current_user is not None and current_user.role == "admin"

    query = (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.slug == slug)
    )
    if not is_admin:
        query = query.filter(Course.is_published == True)  # noqa: E712

    course = query.first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    modules_data = []
    for m in sorted(course.modules, key=lambda x: x.sort_order):
        filtered_lessons = [
            lesson
            for lesson in sorted(m.lessons, key=lambda x: x.sort_order)
            if is_admin or lesson.status != LessonStatus.UNAVAILABLE
        ]
        modules_data.append(
            ModuleWithLessonsResponse(
                id=str(m.id),
                course_id=str(m.course_id),
                title=m.title,
                description=m.description,
                sort_order=m.sort_order,
                created_at=m.created_at,
                updated_at=m.updated_at,
                lessons=[
                    LessonResponse(
                        id=str(lesson.id),
                        module_id=str(lesson.module_id),
                        title=lesson.title,
                        description=lesson.description,
                        mux_playback_id=lesson.mux_playback_id,
                        mux_asset_id=lesson.mux_asset_id,
                        duration_seconds=lesson.duration_seconds,
                        status=lesson.status.value,
                        sort_order=lesson.sort_order,
                        created_at=lesson.created_at,
                        updated_at=lesson.updated_at,
                    )
                    for lesson in filtered_lessons
                ],
            )
        )

    total_lessons = sum(len(m.lessons) for m in modules_data)
    total_duration = sum(lesson.duration_seconds for m in modules_data for lesson in m.lessons)

    return CourseDetailResponse(
        id=str(course.id),
        title=course.title,
        slug=course.slug,
        description=course.description,
        thumbnail_url=course.thumbnail_url,
        difficulty=course.difficulty,
        estimated_hours=course.estimated_hours,
        is_published=course.is_published,
        category=course.category,
        sort_order=course.sort_order,
        content_type=course.content_type,
        learning_title=course.learning_title,
        learning_description=course.learning_description,
        learning_thumbnail_url=course.learning_thumbnail_url,
        sales_page_sections=course.sales_page_sections,
        created_at=course.created_at,
        updated_at=course.updated_at,
        modules=modules_data,
        total_lessons=total_lessons,
        total_duration_seconds=total_duration,
    )


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    request: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> CourseResponse:
    """Update a course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    if request.title is not None:
        course.title = request.title
    if request.slug is not None:
        existing = (
            db.query(Course).filter(Course.slug == request.slug, Course.id != course_id).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kurs z tym slugiem już istnieje",
            )
        course.slug = request.slug
    if request.description is not None:
        course.description = request.description
    if request.thumbnail_url is not None:
        course.thumbnail_url = request.thumbnail_url
    if request.difficulty is not None:
        course.difficulty = request.difficulty
    if request.estimated_hours is not None:
        course.estimated_hours = request.estimated_hours
    if request.is_published is not None:
        course.is_published = request.is_published
    if request.category is not None:
        course.category = request.category
    if request.sort_order is not None:
        course.sort_order = request.sort_order
    if request.content_type is not None:
        course.content_type = request.content_type
    if request.learning_title is not None:
        course.learning_title = request.learning_title or None
    if request.learning_description is not None:
        course.learning_description = request.learning_description or None
    if request.learning_thumbnail_url is not None:
        course.learning_thumbnail_url = request.learning_thumbnail_url or None

    db.commit()
    db.refresh(course)

    return CourseResponse(
        id=str(course.id),
        title=course.title,
        slug=course.slug,
        description=course.description,
        thumbnail_url=course.thumbnail_url,
        difficulty=course.difficulty,
        estimated_hours=course.estimated_hours,
        is_published=course.is_published,
        category=course.category,
        sort_order=course.sort_order,
        content_type=course.content_type,
        learning_title=course.learning_title,
        learning_description=course.learning_description,
        learning_thumbnail_url=course.learning_thumbnail_url,
        sales_page_sections=course.sales_page_sections,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Delete a course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    db.delete(course)
    db.commit()


@router.post(
    "/courses/{course_id}/delete-with-password",
    response_model=DeleteCourseResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_course_with_password(
    course_id: UUID,
    request: DeleteCourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> DeleteCourseResponse:
    """
    Delete a course with password confirmation (admin only).

    This endpoint requires the admin to confirm the operation with their password.
    It deletes the course along with all related data (modules, lessons, enrollments,
    certificates, progress records) and removes associated Mux video assets.

    Returns warnings if any Mux video assets could not be deleted.
    """
    # 1. Verify admin password
    if not security.verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nieprawidłowe hasło",
        )

    # 2. Fetch course with modules and lessons
    course = (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.id == course_id)
        .first()
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    # 3. Delete Mux assets for all lessons, tracking failures
    mux_warnings: list[str] = []
    for module in course.modules:
        for lesson in module.lessons:
            if lesson.mux_asset_id:
                try:
                    mux_service.delete_asset(lesson.mux_asset_id)
                    logger.info(
                        "Deleted Mux asset %s for lesson %s",
                        lesson.mux_asset_id,
                        lesson.id,
                    )
                except Exception as e:
                    warning_msg = (
                        f"Nie udało się usunąć wideo z Mux dla lekcji '{lesson.title}' "
                        f"(asset: {lesson.mux_asset_id})"
                    )
                    mux_warnings.append(warning_msg)
                    logger.warning(
                        "Failed to delete Mux asset %s for lesson %s: %s",
                        lesson.mux_asset_id,
                        lesson.id,
                        e,
                    )

    course_title = course.title

    # 4. Delete course (CASCADE will delete modules, lessons, enrollments, etc.)
    db.delete(course)
    db.commit()

    logger.info(
        "Course %s deleted by admin %s with password confirmation",
        course_id,
        current_user.id,
    )

    return DeleteCourseResponse(
        message=f"Kurs '{course_title}' został usunięty",
        warnings=mux_warnings,
    )


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

    if file.content_type not in THUMBNAIL_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieprawidłowy typ pliku. Dozwolone: PNG, JPG, WebP. "
            f"Otrzymano: {file.content_type}",
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
