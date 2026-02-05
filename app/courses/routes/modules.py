"""Module management routes (admin only)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.courses.models import Course, Module
from app.courses.schemas.course import (
    LessonResponse,
    ModuleCreate,
    ModuleReorderRequest,
    ModuleResponse,
    ModuleUpdate,
    ModuleWithLessonsResponse,
)
from app.db.session import get_db

router = APIRouter()


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
