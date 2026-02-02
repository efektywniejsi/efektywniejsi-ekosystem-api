from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.db.session import get_db
from app.messaging.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
)
from app.messaging.schemas.message import (
    ConversationDetail,
    MessageCreate,
    MessageResponse,
    UserSearchResult,
)
from app.messaging.services.message_service import MessageService

router = APIRouter()


@router.post("/conversations", response_model=ConversationDetail, status_code=201)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    service = MessageService(db)
    return service.create_conversation(current_user, data)


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    service = MessageService(db)
    return service.get_user_conversations(
        user_id=current_user.id,
        page=page,
        limit=limit,
        search=search,
        is_archived=is_archived,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    service = MessageService(db)
    return service.get_conversation_detail(
        conversation_id=conversation_id,
        user_id=current_user.id,
        page=page,
        limit=limit,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = MessageService(db)
    return service.send_message(conversation_id, current_user, data.content)


@router.put("/conversations/{conversation_id}/read", status_code=204)
def mark_as_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = MessageService(db)
    service.mark_as_read(conversation_id, current_user.id)


@router.put("/conversations/{conversation_id}/archive", status_code=204)
def archive_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = MessageService(db)
    service.archive_conversation(conversation_id, current_user.id)


@router.put("/conversations/{conversation_id}/unarchive", status_code=204)
def unarchive_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = MessageService(db)
    service.unarchive_conversation(conversation_id, current_user.id)


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    service = MessageService(db)
    count = await service.get_unread_count_cached(current_user.id)
    return {"unread_count": count}


@router.get("/users/search", response_model=list[UserSearchResult])
def search_users(
    q: str = Query(..., min_length=2, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserSearchResult]:
    service = MessageService(db)
    return service.search_users(q, current_user.id)
