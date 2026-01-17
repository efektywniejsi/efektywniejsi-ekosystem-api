from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models.user import User
from app.courses.models import Course, Lesson, Module
from app.courses.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdate,
    LessonCreate,
    LessonResponse,
    LessonUpdate,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
    ModuleWithLessonsResponse,
)
from app.courses.services.mux_service import MuxService, get_mux_service
from app.db.session import get_db

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
            detail="Course with this slug already exists",
        )

    course = Course(
        title=request.title,
        slug=request.slug,
        description=request.description,
        thumbnail_url=request.thumbnail_url,
        difficulty=request.difficulty,
        estimated_hours=request.estimated_hours,
        is_published=request.is_published,
        is_featured=request.is_featured,
        category=request.category,
        sort_order=request.sort_order,
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
        is_featured=course.is_featured,
        category=course.category,
        sort_order=course.sort_order,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    is_published: bool | None = Query(None, description="Filter by published status"),
    category: str | None = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseResponse]:
    """List all courses (with optional filters)."""
    query = db.query(Course)

    if is_published is not None:
        query = query.filter(Course.is_published == is_published)

    if category:
        query = query.filter(Course.category == category)

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
            is_featured=c.is_featured,
            category=c.category,
            sort_order=c.sort_order,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in courses
    ]


@router.get("/courses/{slug}", response_model=CourseDetailResponse)
async def get_course(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseDetailResponse:
    """Get course details with modules and lessons."""
    course = (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.slug == slug)
        .first()
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    total_lessons = sum(len(module.lessons) for module in course.modules)
    total_duration = sum(
        lesson.duration_seconds for module in course.modules for lesson in module.lessons
    )

    return CourseDetailResponse(
        id=str(course.id),
        title=course.title,
        slug=course.slug,
        description=course.description,
        thumbnail_url=course.thumbnail_url,
        difficulty=course.difficulty,
        estimated_hours=course.estimated_hours,
        is_published=course.is_published,
        is_featured=course.is_featured,
        category=course.category,
        sort_order=course.sort_order,
        created_at=course.created_at,
        updated_at=course.updated_at,
        modules=[
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
                        sort_order=lesson.sort_order,
                        created_at=lesson.created_at,
                        updated_at=lesson.updated_at,
                    )
                    for lesson in sorted(m.lessons, key=lambda x: x.sort_order)
                ],
            )
            for m in sorted(course.modules, key=lambda x: x.sort_order)
        ],
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
            detail="Course not found",
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
                detail="Course with this slug already exists",
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
    if request.is_featured is not None:
        course.is_featured = request.is_featured
    if request.category is not None:
        course.category = request.category
    if request.sort_order is not None:
        course.sort_order = request.sort_order

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
        is_featured=course.is_featured,
        category=course.category,
        sort_order=course.sort_order,
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
            detail="Course not found",
        )

    db.delete(course)
    db.commit()


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
            detail="Course not found",
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
            detail="Module not found",
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
            detail="Module not found",
        )

    # Check if module has any lessons
    if module.lessons:
        lesson_count = len(module.lessons)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete module with {lesson_count} lesson(s). "
            "Please delete all lessons first.",
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
            detail="Module not found",
        )

    lesson = Lesson(
        module_id=module_id,
        title=request.title,
        description=request.description,
        mux_playback_id=request.mux_playback_id,
        mux_asset_id=request.mux_asset_id,
        duration_seconds=request.duration_seconds,
        is_preview=request.is_preview,
        sort_order=request.sort_order,
    )
    db.add(lesson)
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
            detail="Lesson not found",
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
            detail="Lesson not found",
        )

    # Delete Mux asset if present
    if lesson.mux_asset_id:
        try:
            mux_service.delete_asset(lesson.mux_asset_id)
        except Exception as e:
            # Log warning but don't fail the deletion
            # The asset might already be deleted or Mux might be unavailable
            print(f"Warning: Failed to delete Mux asset {lesson.mux_asset_id}: {e}")

    db.delete(lesson)
    db.commit()
