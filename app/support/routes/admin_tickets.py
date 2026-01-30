import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.support.schemas.message import MessageCreate
from app.support.schemas.ticket import (
    TicketDetailResponse,
    TicketListResponse,
    TicketMessageResponse,
    TicketPriorityUpdate,
    TicketStatusUpdate,
)
from app.support.services.ticket_service import TicketService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/support/tickets", response_model=TicketListResponse)
def get_all_tickets(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    service = TicketService(db)
    return service.get_all_tickets(
        status_filter=status,
        priority=priority,
        category=category,
        search=search,
        page=page,
        limit=limit,
    )


@router.get("/support/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    service = TicketService(db)
    ticket = service.get_ticket_by_id(ticket_id)
    return service.build_detail_response(ticket)


@router.post(
    "/support/tickets/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    status_code=201,
)
def admin_reply(
    ticket_id: UUID,
    data: MessageCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TicketMessageResponse:
    service = TicketService(db)
    message = service.add_message(ticket_id, admin, data.content, is_admin=True)

    try:
        from app.support.tasks import send_ticket_reply_notification

        send_ticket_reply_notification.delay(
            str(ticket_id),
            data.content[:200],
        )
    except Exception:
        logger.exception("Failed to dispatch ticket reply notification for %s", ticket_id)

    return TicketMessageResponse(
        id=message.id,
        ticket_id=message.ticket_id,
        author={
            "id": admin.id,
            "name": admin.name,
            "avatar_url": admin.avatar_url,
        },
        content=message.content,
        is_admin_reply=message.is_admin_reply,
        created_at=message.created_at,
    )


@router.patch(
    "/support/tickets/{ticket_id}/status",
    response_model=TicketDetailResponse,
)
def update_status(
    ticket_id: UUID,
    data: TicketStatusUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    service = TicketService(db)
    service.update_status(ticket_id, data.status.value)
    ticket = service.get_ticket_by_id(ticket_id)
    return service.build_detail_response(ticket)


@router.patch(
    "/support/tickets/{ticket_id}/priority",
    response_model=TicketDetailResponse,
)
def update_priority(
    ticket_id: UUID,
    data: TicketPriorityUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    service = TicketService(db)
    service.update_priority(ticket_id, data.priority.value)
    ticket = service.get_ticket_by_id(ticket_id)
    return service.build_detail_response(ticket)
