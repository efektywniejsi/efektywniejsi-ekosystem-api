import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
from app.support.models.message import TicketMessage
from app.support.models.ticket import SupportTicket, TicketStatus
from app.support.schemas.ticket import (
    MessageAuthor,
    TicketCreate,
    TicketDetailResponse,
    TicketListItem,
    TicketListResponse,
    TicketMessageResponse,
)

logger = logging.getLogger(__name__)


class TicketService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_ticket(self, user: User, data: TicketCreate) -> SupportTicket:
        ticket = SupportTicket(
            user_id=user.id,
            subject=data.subject,
            description=data.description,
            category=data.category.value,
            priority=data.priority.value,
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get_user_tickets(
        self, user_id: UUID, status_filter: str | None = None
    ) -> list[TicketListItem]:
        query = self.db.query(SupportTicket).filter(SupportTicket.user_id == user_id)
        if status_filter:
            query = query.filter(SupportTicket.status == status_filter)
        tickets = query.order_by(SupportTicket.updated_at.desc()).all()
        return [self._build_list_item(t) for t in tickets]

    def get_all_tickets(
        self,
        status_filter: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> TicketListResponse:
        query = self.db.query(SupportTicket)

        if status_filter:
            query = query.filter(SupportTicket.status == status_filter)
        if priority:
            query = query.filter(SupportTicket.priority == priority)
        if category:
            query = query.filter(SupportTicket.category == category)
        if search:
            query = query.filter(SupportTicket.subject.ilike(f"%{search}%"))

        total = query.count()
        tickets = (
            query.order_by(SupportTicket.updated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        items = [self._build_list_item(t) for t in tickets]
        return TicketListResponse(tickets=items, total=total)

    def get_ticket_for_user(self, ticket_id: UUID, user_id: UUID) -> SupportTicket:
        ticket: SupportTicket | None = (
            self.db.query(SupportTicket)
            .options(joinedload(SupportTicket.messages).joinedload(TicketMessage.author))
            .filter(SupportTicket.id == ticket_id, SupportTicket.user_id == user_id)
            .first()
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )
        return ticket

    def get_ticket_by_id(self, ticket_id: UUID) -> SupportTicket:
        ticket: SupportTicket | None = (
            self.db.query(SupportTicket)
            .options(
                joinedload(SupportTicket.messages).joinedload(TicketMessage.author),
                joinedload(SupportTicket.user),
            )
            .filter(SupportTicket.id == ticket_id)
            .first()
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )
        return ticket

    def add_message(
        self,
        ticket_id: UUID,
        author: User,
        content: str,
        is_admin: bool = False,
    ) -> TicketMessage:
        ticket = self.get_ticket_by_id(ticket_id)

        message = TicketMessage(
            ticket_id=ticket_id,
            author_id=author.id,
            content=content,
            is_admin_reply=is_admin,
        )
        self.db.add(message)

        if is_admin and ticket.status == TicketStatus.OPEN.value:
            ticket.status = TicketStatus.IN_PROGRESS.value

        self.db.commit()
        self.db.refresh(message)
        return message

    def update_status(self, ticket_id: UUID, new_status: str) -> SupportTicket:
        ticket = self.get_ticket_by_id(ticket_id)
        ticket.status = new_status
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def update_priority(self, ticket_id: UUID, new_priority: str) -> SupportTicket:
        ticket = self.get_ticket_by_id(ticket_id)
        ticket.priority = new_priority
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def close_ticket(self, ticket_id: UUID, user_id: UUID) -> SupportTicket:
        ticket = self.get_ticket_for_user(ticket_id, user_id)
        ticket.status = TicketStatus.CLOSED.value
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def _build_list_item(self, ticket: SupportTicket) -> TicketListItem:
        last_msg = (
            self.db.query(TicketMessage.content)
            .filter(TicketMessage.ticket_id == ticket.id)
            .order_by(TicketMessage.created_at.desc())
            .first()
        )
        return TicketListItem(
            id=ticket.id,
            subject=ticket.subject,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            last_message=last_msg[0] if last_msg else None,
        )

    def build_detail_response(self, ticket: SupportTicket) -> TicketDetailResponse:
        return TicketDetailResponse(
            id=ticket.id,
            subject=ticket.subject,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            user=MessageAuthor(
                id=ticket.user.id,
                name=ticket.user.name,
                avatar_url=ticket.user.avatar_url,
            ),
            messages=[
                TicketMessageResponse(
                    id=msg.id,
                    ticket_id=msg.ticket_id,
                    author=MessageAuthor(
                        id=msg.author.id,
                        name=msg.author.name,
                        avatar_url=msg.author.avatar_url,
                    ),
                    content=msg.content,
                    is_admin_reply=msg.is_admin_reply,
                    created_at=msg.created_at,
                )
                for msg in ticket.messages
            ],
        )
