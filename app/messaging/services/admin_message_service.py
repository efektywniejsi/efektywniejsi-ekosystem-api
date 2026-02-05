"""Admin messaging operations service."""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
from app.messaging.models.conversation import Conversation
from app.messaging.models.conversation_participant import ConversationParticipant
from app.messaging.models.message import Message
from app.messaging.schemas.conversation import (
    ConversationListItem,
    ConversationListResponse,
    MessagePreview,
    ParticipantInfo,
)
from app.messaging.schemas.message import ConversationDetail, MessageResponse

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AdminMessageService:
    """Service for admin message operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_conversations(
        self,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
    ) -> ConversationListResponse:
        """Get all conversations for admin view."""
        query = self.db.query(Conversation)

        if search:
            participant_sub = (
                self.db.query(ConversationParticipant.conversation_id)
                .join(User, User.id == ConversationParticipant.user_id)
                .filter(User.name.ilike(f"%{_escape_like(search)}%"))
                .scalar_subquery()
            )
            query = query.filter(Conversation.id.in_(participant_sub))

        total = query.count()
        conversations = (
            query.order_by(Conversation.updated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        items = []
        for conv in conversations:
            participants = (
                self.db.query(ConversationParticipant)
                .options(joinedload(ConversationParticipant.user))
                .filter(ConversationParticipant.conversation_id == conv.id)
                .all()
            )
            first_participant = participants[0] if participants else None
            other_participant = participants[1] if len(participants) > 1 else first_participant

            last_msg = (
                self.db.query(Message)
                .options(joinedload(Message.sender))
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .first()
            )

            items.append(
                ConversationListItem(
                    id=conv.id,
                    subject=conv.subject,
                    other_participant=self._build_participant_info(
                        other_participant.user if other_participant else first_participant.user  # type: ignore[union-attr]
                    )
                    if (other_participant or first_participant)
                    else ParticipantInfo(
                        id=UUID(int=0), name="Usunięty", avatar_url=None, role="paid"
                    ),
                    last_message=MessagePreview(
                        content=last_msg.content[:100],
                        sender_name=last_msg.sender.name,
                        created_at=last_msg.created_at,
                    )
                    if last_msg
                    else None,
                    unread_count=0,
                    is_archived=conv.is_archived,
                    updated_at=conv.updated_at,
                )
            )

        return ConversationListResponse(conversations=items, total=total)

    def get_conversation(self, conversation_id: UUID) -> ConversationDetail:
        """Get conversation detail for admin."""
        conversation = (
            self.db.query(Conversation)
            .options(
                joinedload(Conversation.participants).joinedload(ConversationParticipant.user),
            )
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Konwersacja nie znaleziona",
            )

        total_messages = (
            self.db.query(func.count(Message.id))
            .filter(Message.conversation_id == conversation_id)
            .scalar()
            or 0
        )

        messages = (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        participants_info = [
            self._build_participant_info(p.user) for p in conversation.participants
        ]

        message_responses = [
            MessageResponse(
                id=m.id,
                sender=self._build_participant_info(m.sender),
                content=m.content,
                is_system_message=m.is_system_message,
                created_at=m.created_at,
                edited_at=m.edited_at,
            )
            for m in messages
        ]

        return ConversationDetail(
            id=conversation.id,
            subject=conversation.subject,
            participants=participants_info,
            messages=message_responses,
            total_messages=total_messages,
        )

    def delete_message(self, message_id: UUID) -> None:
        """Delete a message (admin only)."""
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wiadomość nie znaleziona",
            )
        self.db.delete(message)
        self.db.commit()

    @staticmethod
    def _build_participant_info(user: User) -> ParticipantInfo:
        """Build participant info from user."""
        return ParticipantInfo(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
        )
