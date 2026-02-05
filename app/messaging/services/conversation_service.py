"""Conversation listing and details service."""

import logging
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
from app.core import redis as redis_module
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


class ConversationService:
    """Service for conversation listing and detail operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_conversations(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        is_archived: bool = False,
    ) -> ConversationListResponse:
        """Get paginated list of user's conversations."""
        participant_sub = (
            self.db.query(ConversationParticipant.conversation_id)
            .filter(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_deleted == is_archived,
            )
            .scalar_subquery()
        )

        query = self.db.query(Conversation).filter(Conversation.id.in_(participant_sub))

        if search:
            other_participant_sub = (
                self.db.query(ConversationParticipant.conversation_id)
                .join(User, User.id == ConversationParticipant.user_id)
                .filter(
                    ConversationParticipant.user_id != user_id,
                    User.name.ilike(f"%{_escape_like(search)}%"),
                )
                .scalar_subquery()
            )
            query = query.filter(Conversation.id.in_(other_participant_sub))

        total = query.count()
        conversations = (
            query.order_by(Conversation.updated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        items = [self._build_list_item(conv, user_id) for conv in conversations]
        return ConversationListResponse(conversations=items, total=total)

    def get_conversation_detail(
        self,
        conversation_id: UUID,
        user_id: UUID,
        page: int = 1,
        limit: int = 50,
    ) -> ConversationDetail:
        """Get conversation detail with messages."""
        from datetime import UTC, datetime

        participant = self._get_participant_or_403(conversation_id, user_id)

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
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        participant.last_read_at = datetime.now(UTC)
        self.db.commit()
        self._invalidate_unread_cache(user_id)

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

    def archive_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        """Archive a conversation for a user."""
        participant = self._get_participant_or_403(conversation_id, user_id)
        participant.is_deleted = True
        self.db.commit()

    def unarchive_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        """Unarchive a conversation for a user."""
        participant = self._get_participant_or_403(conversation_id, user_id)
        participant.is_deleted = False
        self.db.commit()

    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of conversations with unread messages."""
        participants = (
            self.db.query(ConversationParticipant)
            .filter(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.is_deleted == False,  # noqa: E712
            )
            .all()
        )

        unread = 0
        for p in participants:
            query = self.db.query(func.count(Message.id)).filter(
                Message.conversation_id == p.conversation_id,
                Message.sender_id != user_id,
            )
            if p.last_read_at:
                query = query.filter(Message.created_at > p.last_read_at)
            count = query.scalar() or 0
            if count > 0:
                unread += 1

        return unread

    async def get_unread_count_cached(self, user_id: UUID) -> int:
        """Get unread count with Redis caching."""
        cache_key = f"dm:unread:{user_id}"
        try:
            if redis_module.redis_client:
                cached = await redis_module.redis_client.get(cache_key)
                if cached is not None:
                    return int(cached)
        except Exception:
            logger.warning("Redis cache read failed for unread count")

        count = self.get_unread_count(user_id)

        try:
            if redis_module.redis_client:
                await redis_module.redis_client.setex(cache_key, 30, str(count))
        except Exception:
            logger.warning("Redis cache write failed for unread count")

        return count

    def _get_participant_or_403(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant:
        """Get participant or raise 403 if not found."""
        participant = (
            self.db.query(ConversationParticipant)
            .filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
            .first()
        )
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Brak dostępu do tej konwersacji",
            )
        return cast(ConversationParticipant, participant)

    def _build_list_item(
        self, conversation: Conversation, current_user_id: UUID
    ) -> ConversationListItem:
        """Build a conversation list item."""
        participants = (
            self.db.query(ConversationParticipant)
            .options(joinedload(ConversationParticipant.user))
            .filter(ConversationParticipant.conversation_id == conversation.id)
            .all()
        )

        other = next(
            (p for p in participants if p.user_id != current_user_id),
            participants[0] if participants else None,
        )

        current = next(
            (p for p in participants if p.user_id == current_user_id),
            None,
        )

        last_msg = (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .first()
        )

        unread_query = self.db.query(func.count(Message.id)).filter(
            Message.conversation_id == conversation.id,
            Message.sender_id != current_user_id,
        )
        if current and current.last_read_at:
            unread_query = unread_query.filter(Message.created_at > current.last_read_at)
        unread_count = unread_query.scalar() or 0

        return ConversationListItem(
            id=conversation.id,
            subject=conversation.subject,
            other_participant=self._build_participant_info(other.user)
            if other
            else ParticipantInfo(id=UUID(int=0), name="Usunięty", avatar_url=None, role="paid"),
            last_message=MessagePreview(
                content=last_msg.content[:100],
                sender_name=last_msg.sender.name,
                created_at=last_msg.created_at,
            )
            if last_msg
            else None,
            unread_count=unread_count,
            is_archived=current.is_deleted if current else False,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _build_participant_info(user: User) -> ParticipantInfo:
        """Build participant info from user."""
        return ParticipantInfo(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
        )

    @staticmethod
    def _invalidate_unread_cache(user_id: UUID) -> None:
        """Invalidate Redis cache for unread count."""
        try:
            if redis_module.redis_client:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(redis_module.redis_client.delete(f"dm:unread:{user_id}"))
        except Exception:
            logger.warning("Failed to invalidate unread cache for user %s", user_id)
