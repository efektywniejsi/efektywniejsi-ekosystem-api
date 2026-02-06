"""Admin lesson management routes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.courses.models import Lesson, LessonStatus, Module
from app.courses.schemas.course import (
    LessonCreate,
    LessonReorderRequest,
    LessonResponse,
    LessonUpdate,
)
from app.courses.services.mux_service import MuxService, get_mux_service
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


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

    if lesson.mux_asset_id:
        try:
            mux_service.delete_asset(lesson.mux_asset_id)
        except Exception as e:
            logger.warning("Failed to delete Mux asset %s: %s", lesson.mux_asset_id, e)

    db.delete(lesson)
    db.commit()


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

    lesson_ids = [UUID(lid) for lid in request.lesson_ids]
    lessons = db.query(Lesson).filter(Lesson.id.in_(lesson_ids)).all()

    if len(lessons) != len(lesson_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeden lub więcej identyfikatorów lekcji jest nieprawidłowych",
        )

    for lesson in lessons:
        if lesson.module_id != module_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lekcja {lesson.id} nie należy do tego modułu",
            )

    for index, lesson_id in enumerate(lesson_ids):
        lesson = next(les for les in lessons if les.id == lesson_id)
        lesson.sort_order = index

    db.commit()

    return {"message": "Kolejność lekcji zmieniona"}
