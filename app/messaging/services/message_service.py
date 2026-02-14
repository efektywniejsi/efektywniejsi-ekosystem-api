import logging
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
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

            self.db.commit()
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
    ) -> ConversationListResponse:
        participant_sub = (
            self.db.query(ConversationParticipant.conversation_id)
            .filter(
                ConversationParticipant.user_id == user_id,
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

        if not conversations:
            return ConversationListResponse(conversations=[], total=total)

        conv_ids = [c.id for c in conversations]

        # Batch load participants for all conversations
        all_participants = (
            self.db.query(ConversationParticipant)
            .options(joinedload(ConversationParticipant.user))
            .filter(ConversationParticipant.conversation_id.in_(conv_ids))
            .all()
        )
        participants_by_conv: dict[UUID, list[ConversationParticipant]] = {}
        for p in all_participants:
            participants_by_conv.setdefault(p.conversation_id, []).append(p)

        # Batch load last messages using a window function
        last_msg_sub = (
            self.db.query(
                Message.id,
                Message.conversation_id,
                func.row_number()
                .over(
                    partition_by=Message.conversation_id,
                    order_by=Message.created_at.desc(),
                )
                .label("rn"),
            )
            .filter(Message.conversation_id.in_(conv_ids))
            .subquery()
        )
        last_messages = (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .join(last_msg_sub, Message.id == last_msg_sub.c.id)
            .filter(last_msg_sub.c.rn == 1)
            .all()
        )
        last_msg_by_conv = {m.conversation_id: m for m in last_messages}

        # Batch load unread counts
        unread_sub = (
            self.db.query(
                Message.conversation_id,
                func.count(Message.id).label("unread"),
            )
            .join(
                ConversationParticipant,
                (ConversationParticipant.conversation_id == Message.conversation_id)
                & (ConversationParticipant.user_id == user_id),
            )
            .filter(
                Message.conversation_id.in_(conv_ids),
                Message.sender_id != user_id,
                or_(
                    ConversationParticipant.last_read_at.is_(None),
                    Message.created_at > ConversationParticipant.last_read_at,
                ),
            )
            .group_by(Message.conversation_id)
            .all()
        )
        unread_by_conv = {row[0]: row[1] for row in unread_sub}

        items = []
        for conv in conversations:
            participants = participants_by_conv.get(conv.id, [])
            other = next(
                (p for p in participants if p.user_id != user_id),
                participants[0] if participants else None,
            )
            last_msg = last_msg_by_conv.get(conv.id)

            items.append(
                ConversationListItem(
                    id=conv.id,
                    subject=conv.subject,
                    other_participant=self._build_participant_info(other.user)
                    if other
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
                    unread_count=unread_by_conv.get(conv.id, 0),
                    updated_at=conv.updated_at,
                )
            )

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

    def get_unread_count(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(func.distinct(ConversationParticipant.conversation_id)))
            .join(Message, Message.conversation_id == ConversationParticipant.conversation_id)
            .filter(
                ConversationParticipant.user_id == user_id,
                Message.sender_id != user_id,
                or_(
                    ConversationParticipant.last_read_at.is_(None),
                    Message.created_at > ConversationParticipant.last_read_at,
                ),
            )
            .scalar()
        ) or 0

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

    @staticmethod
    def _build_participant_info(user: User) -> ParticipantInfo:
        return ParticipantInfo(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
        )
