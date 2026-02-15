from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.processes.schemas import (
    LessonProcessCreate,
    LessonProcessResponse,
    ProcessCreate,
    ProcessResponse,
    ProcessUpdate,
)
from app.processes.services import ProcessService

router = APIRouter()


@router.get("/processes", response_model=list[ProcessResponse])
def list_all_processes(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ProcessResponse]:
    """List all processes (including unpublished) - Admin only."""
    service = ProcessService(db)
    return service.get_all_processes()


@router.get("/processes/{process_id}", response_model=ProcessResponse)
def get_process_by_id(
    process_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProcessResponse:
    """Get process details by ID - Admin only."""
    service = ProcessService(db)
    return service.get_process_by_id(process_id)


@router.post("/processes", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
def create_process(
    data: ProcessCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProcessResponse:
    """Create a new process - Admin only."""
    service = ProcessService(db)
    return service.create_process(data)


@router.patch("/processes/{process_id}", response_model=ProcessResponse)
def update_process(
    process_id: UUID,
    data: ProcessUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProcessResponse:
    """Update a process - Admin only."""
    service = ProcessService(db)
    return service.update_process(process_id, data)


@router.delete("/processes/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process(
    process_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete a process - Admin only."""
    service = ProcessService(db)
    service.delete_process(process_id)


# ─────────────────────────────────────────────────────────────
# Lesson Process Endpoints
# ─────────────────────────────────────────────────────────────


@router.post(
    "/lessons/{lesson_id}/processes",
    response_model=LessonProcessResponse,
    status_code=status.HTTP_201_CREATED,
)
def attach_process_to_lesson(
    lesson_id: UUID,
    data: LessonProcessCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LessonProcessResponse:
    """Attach a process to a lesson - Admin only."""
    service = ProcessService(db)
    return service.attach_process_to_lesson(lesson_id, data)


@router.delete(
    "/lessons/{lesson_id}/processes/{process_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def detach_process_from_lesson(
    lesson_id: UUID,
    process_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Detach a process from a lesson - Admin only."""
    service = ProcessService(db)
    service.detach_process_from_lesson(lesson_id, process_id)
