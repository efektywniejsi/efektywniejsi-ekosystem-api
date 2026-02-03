import logging
from datetime import UTC, datetime
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
    ConversationCreate,
    ConversationListItem,
    ConversationListResponse,
    MessagePreview,
    ParticipantInfo,
)
from app.messaging.schemas.message import (
    ConversationDetail,
    MessageResponse,
    UserSearchResult,
)

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MessageService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_conversation(self, sender: User, data: ConversationCreate) -> ConversationDetail:
        if data.recipient_id == sender.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nie możesz wysłać wiadomości do siebie",
            )

        recipient = self.db.query(User).filter(User.id == data.recipient_id).first()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Użytkownik nie znaleziony",
            )

        existing_conv = self._find_existing_conversation(sender.id, data.recipient_id)

        if existing_conv:
            message = Message(
                conversation_id=existing_conv.id,
                sender_id=sender.id,
                content=data.initial_message,
            )
            self.db.add(message)
            existing_conv.updated_at = datetime.now(UTC)

            participant = (
                self.db.query(ConversationParticipant)
                .filter(
                    ConversationParticipant.conversation_id == existing_conv.id,
                    ConversationParticipant.user_id == sender.id,
                )
                .first()
            )
            if participant and participant.is_deleted:
                participant.is_deleted = False

            self.db.commit()
            self._invalidate_unread_cache(data.recipient_id)
            self._send_dm_notification(
                recipient_user_id=data.recipient_id,
                sender=sender,
                message_content=data.initial_message,
                conversation_id=existing_conv.id,
            )
            return self.get_conversation_detail(existing_conv.id, sender.id)

        conversation = Conversation(subject=data.subject)
        self.db.add(conversation)
        self.db.flush()

        sender_participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=sender.id,
            last_read_at=datetime.now(UTC),
        )
        recipient_participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=data.recipient_id,
        )
        self.db.add(sender_participant)
        self.db.add(recipient_participant)

        message = Message(
            conversation_id=conversation.id,
            sender_id=sender.id,
            content=data.initial_message,
        )
        self.db.add(message)

        self.db.commit()
        self._invalidate_unread_cache(data.recipient_id)
        self._send_dm_notification(
            recipient_user_id=data.recipient_id,
            sender=sender,
            message_content=data.initial_message,
            conversation_id=conversation.id,
        )
        return self.get_conversation_detail(conversation.id, sender.id)

    def get_user_conversations(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        is_archived: bool = False,
    ) -> ConversationListResponse:
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

        items = [self._build_conversation_list_item(conv, user_id) for conv in conversations]

        return ConversationListResponse(conversations=items, total=total)

    def get_conversation_detail(
        self,
        conversation_id: UUID,
        user_id: UUID,
        page: int = 1,
        limit: int = 50,
    ) -> ConversationDetail:
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

    def send_message(self, conversation_id: UUID, sender: User, content: str) -> MessageResponse:
        self._get_participant_or_403(conversation_id, sender.id)

        message = Message(
            conversation_id=conversation_id,
            sender_id=sender.id,
            content=content,
        )
        self.db.add(message)

        conversation = (
            self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        if conversation:
            conversation.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(message)

        other_participants = (
            self.db.query(ConversationParticipant)
            .filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != sender.id,
            )
            .all()
        )
        for p in other_participants:
            self._invalidate_unread_cache(p.user_id)
            self._send_dm_notification(
                recipient_user_id=p.user_id,
                sender=sender,
                message_content=content,
                conversation_id=conversation_id,
            )

        return MessageResponse(
            id=message.id,
            sender=self._build_participant_info(sender),
            content=message.content,
            is_system_message=message.is_system_message,
            created_at=message.created_at,
            edited_at=message.edited_at,
        )

    def mark_as_read(self, conversation_id: UUID, user_id: UUID) -> None:
        participant = self._get_participant_or_403(conversation_id, user_id)
        participant.last_read_at = datetime.now(UTC)
        self.db.commit()
        self._invalidate_unread_cache(user_id)

    def archive_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        participant = self._get_participant_or_403(conversation_id, user_id)
        participant.is_deleted = True
        self.db.commit()

    def unarchive_conversation(self, conversation_id: UUID, user_id: UUID) -> None:
        participant = self._get_participant_or_403(conversation_id, user_id)
        participant.is_deleted = False
        self.db.commit()

    def get_unread_count(self, user_id: UUID) -> int:
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

    def admin_get_conversations(
        self,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
    ) -> ConversationListResponse:
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

    def admin_get_conversation(self, conversation_id: UUID) -> ConversationDetail:
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

    def admin_delete_message(self, message_id: UUID) -> None:
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wiadomość nie znaleziona",
            )
        self.db.delete(message)
        self.db.commit()

    def search_users(
        self, query: str, current_user_id: UUID, limit: int = 10
    ) -> list[UserSearchResult]:
        if len(query) < 2:
            return []

        users = (
            self.db.query(User)
            .filter(
                User.id != current_user_id,
                User.is_active == True,  # noqa: E712
                User.name.ilike(f"%{_escape_like(query)}%"),
            )
            .limit(limit)
            .all()
        )

        return [
            UserSearchResult(
                id=u.id,
                name=u.name,
                avatar_url=u.avatar_url,
                role=u.role,
            )
            for u in users
        ]

    @staticmethod
    def _send_dm_notification(
        recipient_user_id: UUID,
        sender: User,
        message_content: str,
        conversation_id: UUID,
    ) -> None:
        try:
            from app.notifications.tasks import send_direct_message_notification

            send_direct_message_notification.delay(
                recipient_user_id=str(recipient_user_id),
                sender_user_id=str(sender.id),
                message_preview=message_content[:200],
                conversation_id=str(conversation_id),
            )
        except (ImportError, AttributeError) as exc:
            logger.error("Celery task import failed: %s", exc, exc_info=True)
        except Exception as exc:
            logger.warning(
                "Failed to enqueue DM notification for user %s: %s", recipient_user_id, exc
            )

    def _find_existing_conversation(self, user1_id: UUID, user2_id: UUID) -> Conversation | None:
        user1_convs = (
            self.db.query(ConversationParticipant.conversation_id)
            .filter(ConversationParticipant.user_id == user1_id)
            .scalar_subquery()
        )
        user2_convs = (
            self.db.query(ConversationParticipant.conversation_id)
            .filter(ConversationParticipant.user_id == user2_id)
            .scalar_subquery()
        )

        conversation = (
            self.db.query(Conversation)
            .filter(
                Conversation.id.in_(user1_convs),
                Conversation.id.in_(user2_convs),
            )
            .first()
        )
        return cast(Conversation | None, conversation)

    def _get_participant_or_403(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant:
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

    def _build_conversation_list_item(
        self, conversation: Conversation, current_user_id: UUID
    ) -> ConversationListItem:
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
        return ParticipantInfo(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
        )

    @staticmethod
    def _invalidate_unread_cache(user_id: UUID) -> None:
        try:
            if redis_module.redis_client:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(redis_module.redis_client.delete(f"dm:unread:{user_id}"))
        except Exception:
            logger.warning("Failed to invalidate unread cache for user %s", user_id)
