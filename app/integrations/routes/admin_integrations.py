from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationDetailResponse,
    IntegrationResponse,
    IntegrationUpdate,
    LessonIntegrationCreate,
    LessonIntegrationResponse,
)
from app.integrations.services import IntegrationService

router = APIRouter()


@router.get("/integrations", response_model=list[IntegrationResponse])
def list_all_integrations(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[IntegrationResponse]:
    """List all integrations (including unpublished) - Admin only."""
    service = IntegrationService(db)
    return service.get_all_integrations()


@router.get("/integrations/{integration_id}", response_model=IntegrationDetailResponse)
def get_integration_by_id(
    integration_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntegrationDetailResponse:
    """Get integration details by ID - Admin only."""
    service = IntegrationService(db)
    return service.get_integration_by_id(integration_id)


@router.post(
    "/integrations", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED
)
def create_integration(
    data: IntegrationCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    """Create a new integration - Admin only."""
    service = IntegrationService(db)
    return service.create_integration(data, admin)


@router.patch("/integrations/{integration_id}", response_model=IntegrationResponse)
def update_integration(
    integration_id: UUID,
    data: IntegrationUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    """Update an integration - Admin only."""
    service = IntegrationService(db)
    return service.update_integration(integration_id, data)


@router.delete("/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    integration_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete an integration - Admin only."""
    service = IntegrationService(db)
    service.delete_integration(integration_id)


@router.post(
    "/lessons/{lesson_id}/integrations",
    response_model=LessonIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def attach_integration_to_lesson(
    lesson_id: UUID,
    data: LessonIntegrationCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LessonIntegrationResponse:
    """Attach integration to a lesson - Admin only."""
    service = IntegrationService(db)
    return service.attach_integration_to_lesson(lesson_id, data)


@router.delete(
    "/lessons/{lesson_id}/integrations/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def detach_integration_from_lesson(
    lesson_id: UUID,
    integration_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Detach integration from a lesson - Admin only."""
    service = IntegrationService(db)
    service.detach_integration_from_lesson(lesson_id, integration_id)
