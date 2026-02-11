from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.db.session import get_db
from app.integrations.schemas import (
    CategoryCountResponse,
    IntegrationDetailResponse,
    IntegrationResponse,
    LessonIntegrationResponse,
    ProcessIntegrationResponse,
)
from app.integrations.services import IntegrationService

router = APIRouter()


@router.get("/integrations", response_model=list[IntegrationResponse])
def list_integrations(
    category: str | None = None,
    search: str | None = None,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IntegrationResponse]:
    """List all published integrations with optional filtering."""
    service = IntegrationService(db)
    return service.get_published_integrations(category=category, search=search)


@router.get("/integrations/categories", response_model=list[CategoryCountResponse])
def list_categories(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CategoryCountResponse]:
    """Get list of all categories with counts."""
    service = IntegrationService(db)
    return service.get_categories_with_counts()


@router.get("/integrations/{slug}", response_model=IntegrationDetailResponse)
def get_integration(
    slug: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrationDetailResponse:
    """Get integration details by slug."""
    service = IntegrationService(db)
    return service.get_integration_by_slug(slug)


@router.get("/lessons/{lesson_id}/integrations", response_model=list[LessonIntegrationResponse])
def get_lesson_integrations(
    lesson_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LessonIntegrationResponse]:
    """Get integrations attached to a lesson."""
    service = IntegrationService(db)
    return service.get_lesson_integrations(lesson_id)


@router.get("/processes/{process_id}/integrations", response_model=list[ProcessIntegrationResponse])
def get_process_integrations(
    process_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProcessIntegrationResponse]:
    """Get integrations attached to a package process."""
    service = IntegrationService(db)
    return service.get_process_integrations(process_id)
