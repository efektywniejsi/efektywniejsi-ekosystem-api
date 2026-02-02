from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.messaging.schemas.conversation import ConversationListResponse
from app.messaging.schemas.message import ConversationDetail
from app.messaging.services.message_service import MessageService

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
def admin_list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    service = MessageService(db)
    return service.admin_get_conversations(page=page, limit=limit, search=search)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def admin_get_conversation(
    conversation_id: UUID,
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    service = MessageService(db)
    return service.admin_get_conversation(conversation_id)


@router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    status_code=204,
)
def admin_delete_message(
    conversation_id: UUID,
    message_id: UUID,
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    service = MessageService(db)
    service.admin_delete_message(message_id)
