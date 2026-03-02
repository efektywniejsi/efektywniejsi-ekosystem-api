from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.db.session import get_db
from app.processes.schemas import LessonProcessResponse, ProcessDetailResponse, ProcessResponse
from app.processes.services import ProcessService

router = APIRouter()


@router.get("/processes", response_model=list[ProcessResponse])
def list_processes(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProcessResponse]:
    """List all published processes."""
    service = ProcessService(db)
    return service.get_published_processes()


@router.get("/processes/slug/{slug}", response_model=ProcessDetailResponse)
def get_process_by_slug(
    slug: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProcessDetailResponse:
    """Get a single published process by slug with lesson usage info."""
    service = ProcessService(db)
    return service.get_published_process_detail_by_slug(slug)


@router.get("/lessons/{lesson_id}/processes", response_model=list[LessonProcessResponse])
def get_lesson_processes(
    lesson_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LessonProcessResponse]:
    """Get processes attached to a lesson."""
    service = ProcessService(db)
    return service.get_lesson_processes(lesson_id)
