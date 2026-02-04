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
from app.core.config import settings
from app.courses.models import Course, Lesson, LessonStatus, Module
from app.courses.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdate,
    LessonCreate,
    LessonReorderRequest,
    LessonResponse,
    LessonUpdate,
    ModuleCreate,
    ModuleReorderRequest,
    ModuleResponse,
    ModuleUpdate,
    ModuleWithLessonsResponse,
)
from app.courses.services.mux_service import MuxService, get_mux_service
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


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
                        is_preview=lesson.is_preview,
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


@router.get("/courses/{course_id}/modules", response_model=list[ModuleResponse])
async def get_course_modules(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[ModuleResponse]:
    """Get all modules for a course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    modules = (
        db.query(Module).filter(Module.course_id == course_id).order_by(Module.sort_order).all()
    )

    return [
        ModuleResponse(
            id=str(m.id),
            course_id=str(m.course_id),
            title=m.title,
            description=m.description,
            sort_order=m.sort_order,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in modules
    ]


@router.get(
    "/courses/{course_id}/modules-with-lessons",
    response_model=list[ModuleWithLessonsResponse],
)
async def get_course_modules_with_lessons(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[ModuleWithLessonsResponse]:
    """Get all modules with their lessons for a course (admin only, no filtering)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    modules = (
        db.query(Module)
        .options(joinedload(Module.lessons))
        .filter(Module.course_id == course_id)
        .order_by(Module.sort_order)
        .all()
    )

    return [
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
                    is_preview=lesson.is_preview,
                    status=lesson.status.value,
                    sort_order=lesson.sort_order,
                    created_at=lesson.created_at,
                    updated_at=lesson.updated_at,
                )
                for lesson in sorted(m.lessons, key=lambda x: x.sort_order)
            ],
        )
        for m in modules
    ]


@router.post(
    "/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    course_id: UUID,
    request: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ModuleResponse:
    """Add a module to a course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    module = Module(
        course_id=course_id,
        title=request.title,
        description=request.description,
        sort_order=request.sort_order,
    )
    db.add(module)
    db.commit()
    db.refresh(module)

    from app.notifications.tasks import send_course_update_notification

    send_course_update_notification.delay(
        course_id=str(course_id),
        update_type="new_module",
        item_title=module.title,
    )

    return ModuleResponse(
        id=str(module.id),
        course_id=str(module.course_id),
        title=module.title,
        description=module.description,
        sort_order=module.sort_order,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.patch("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: UUID,
    request: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ModuleResponse:
    """Update a module (admin only)."""
    module = db.query(Module).filter(Module.id == module_id).first()

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moduł nie znaleziony",
        )

    if request.title is not None:
        module.title = request.title
    if request.description is not None:
        module.description = request.description
    if request.sort_order is not None:
        module.sort_order = request.sort_order

    db.commit()
    db.refresh(module)

    return ModuleResponse(
        id=str(module.id),
        course_id=str(module.course_id),
        title=module.title,
        description=module.description,
        sort_order=module.sort_order,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """Delete a module (admin only). Module must be empty (no lessons)."""
    module = (
        db.query(Module).filter(Module.id == module_id).options(joinedload(Module.lessons)).first()
    )

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moduł nie znaleziony",
        )

    # Check if module has any lessons
    if module.lessons:
        lesson_count = len(module.lessons)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nie można usunąć modułu z {lesson_count} lekcją/lekcjami. "
            "Najpierw usuń wszystkie lekcje.",
        )

    db.delete(module)
    db.commit()


@router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    module_id: UUID,
    request: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LessonResponse:
    """Add a lesson to a module (admin only)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moduł nie znaleziony",
        )

    lesson = Lesson(
        module_id=module_id,
        title=request.title,
        description=request.description,
        mux_playback_id=request.mux_playback_id,
        mux_asset_id=request.mux_asset_id,
        duration_seconds=request.duration_seconds,
        is_preview=request.is_preview,
        status=LessonStatus(request.status),
        sort_order=request.sort_order,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    from app.notifications.tasks import send_course_update_notification

    send_course_update_notification.delay(
        course_id=str(module.course_id),
        update_type="new_lesson",
        item_title=lesson.title,
    )

    return LessonResponse(
        id=str(lesson.id),
        module_id=str(lesson.module_id),
        title=lesson.title,
        description=lesson.description,
        mux_playback_id=lesson.mux_playback_id,
        mux_asset_id=lesson.mux_asset_id,
        duration_seconds=lesson.duration_seconds,
        is_preview=lesson.is_preview,
        status=lesson.status.value,
        sort_order=lesson.sort_order,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


@router.patch("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    request: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LessonResponse:
    """Update a lesson (admin only)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lekcja nie znaleziona",
        )

    if request.title is not None:
        lesson.title = request.title
    if request.description is not None:
        lesson.description = request.description
    if request.mux_playback_id is not None:
        lesson.mux_playback_id = request.mux_playback_id
    if request.mux_asset_id is not None:
        lesson.mux_asset_id = request.mux_asset_id
    if request.duration_seconds is not None:
        lesson.duration_seconds = request.duration_seconds
    if request.is_preview is not None:
        lesson.is_preview = request.is_preview
    if request.status is not None:
        lesson.status = LessonStatus(request.status)
    if request.sort_order is not None:
        lesson.sort_order = request.sort_order

    db.commit()
    db.refresh(lesson)

    return LessonResponse(
        id=str(lesson.id),
        module_id=str(lesson.module_id),
        title=lesson.title,
        description=lesson.description,
        mux_playback_id=lesson.mux_playback_id,
        mux_asset_id=lesson.mux_asset_id,
        duration_seconds=lesson.duration_seconds,
        is_preview=lesson.is_preview,
        status=lesson.status.value,
        sort_order=lesson.sort_order,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> None:
    """Delete a lesson (admin only). Also deletes associated Mux video asset if present."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lekcja nie znaleziona",
        )

    # Delete Mux asset if present
    if lesson.mux_asset_id:
        try:
            mux_service.delete_asset(lesson.mux_asset_id)
        except Exception as e:
            # Log warning but don't fail the deletion
            # The asset might already be deleted or Mux might be unavailable
            logger.warning("Failed to delete Mux asset %s: %s", lesson.mux_asset_id, e)

    db.delete(lesson)
    db.commit()


@router.post("/courses/{course_id}/modules/reorder", status_code=status.HTTP_200_OK)
async def reorder_modules(
    course_id: UUID,
    request: ModuleReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, str]:
    """Reorder modules in a course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kurs nie znaleziony",
        )

    # Verify all module IDs belong to this course
    module_ids = [UUID(mid) for mid in request.module_ids]
    modules = db.query(Module).filter(Module.id.in_(module_ids)).all()

    if len(modules) != len(module_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeden lub więcej identyfikatorów modułów jest nieprawidłowych",
        )

    # Verify all modules belong to this course
    for module in modules:
        if module.course_id != course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Moduł {module.id} nie należy do tego kursu",
            )

    # Update sort_order for each module
    for index, module_id in enumerate(module_ids):
        module = next(m for m in modules if m.id == module_id)
        module.sort_order = index

    db.commit()

    return {"message": "Kolejność modułów zmieniona"}


@router.post("/modules/{module_id}/lessons/reorder", status_code=status.HTTP_200_OK)
async def reorder_lessons(
    module_id: UUID,
    request: LessonReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, str]:
    """Reorder lessons in a module (admin only)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moduł nie znaleziony",
        )

    # Verify all lesson IDs belong to this module
    lesson_ids = [UUID(lid) for lid in request.lesson_ids]
    lessons = db.query(Lesson).filter(Lesson.id.in_(lesson_ids)).all()

    if len(lessons) != len(lesson_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeden lub więcej identyfikatorów lekcji jest nieprawidłowych",
        )

    # Verify all lessons belong to this module
    for lesson in lessons:
        if lesson.module_id != module_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lekcja {lesson.id} nie należy do tego modułu",
            )

    # Update sort_order for each lesson
    for index, lesson_id in enumerate(lesson_ids):
        lesson = next(les for les in lessons if les.id == lesson_id)
        lesson.sort_order = index

    db.commit()

    return {"message": "Kolejność lekcji zmieniona"}


THUMBNAIL_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"]


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
