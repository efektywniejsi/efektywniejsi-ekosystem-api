import uuid
from datetime import datetime

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AiChatSession(Base):
    __tablename__ = "ai_chat_sessions"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_ai_chat_entity"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    entity_type: Mapped[str] = mapped_column(String(10), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    pending_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pending_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
