from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.db.session import get_db
from app.support.schemas.message import MessageCreate
from app.support.schemas.ticket import (
    TicketCreate,
    TicketDetailResponse,
    TicketListItem,
    TicketMessageResponse,
)
from app.support.services.ticket_service import TicketService

router = APIRouter()


@router.post("/tickets", response_model=TicketDetailResponse, status_code=201)
def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    service = TicketService(db)
    ticket = service.create_ticket(current_user, data)
    reloaded = service.get_ticket_for_user(ticket.id, current_user.id)
    return service.build_detail_response(reloaded)


@router.get("/tickets/me", response_model=list[TicketListItem])
def get_my_tickets(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TicketListItem]:
    service = TicketService(db)
    return service.get_user_tickets(current_user.id, status)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    service = TicketService(db)
    ticket = service.get_ticket_for_user(ticket_id, current_user.id)
    return service.build_detail_response(ticket)


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    status_code=201,
)
def reply_to_ticket(
    ticket_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketMessageResponse:
    service = TicketService(db)
    service.get_ticket_for_user(ticket_id, current_user.id)
    message = service.add_message(ticket_id, current_user, data.content, is_admin=False)
    return TicketMessageResponse(
        id=message.id,
        ticket_id=message.ticket_id,
        author={
            "id": current_user.id,
            "name": current_user.name,
            "avatar_url": current_user.avatar_url,
        },
        content=message.content,
        is_admin_reply=message.is_admin_reply,
        created_at=message.created_at,
    )


@router.patch("/tickets/{ticket_id}/close", response_model=TicketDetailResponse)
def close_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    service = TicketService(db)
    service.close_ticket(ticket_id, current_user.id)
    ticket = service.get_ticket_for_user(ticket_id, current_user.id)
    return service.build_detail_response(ticket)
