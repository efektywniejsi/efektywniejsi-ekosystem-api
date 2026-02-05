"""Reply operations service for community threads."""

import logging
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.community.models.reply import ThreadReply
from app.community.models.thread import CommunityThread, ThreadStatus

logger = logging.getLogger(__name__)


class ReplyService:
    """Service for thread reply operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add_reply(self, thread_id: UUID, author: User, content: str) -> ThreadReply:
        """Add a reply to a thread."""
        thread = self._get_thread_or_404(thread_id)

        if thread.status == ThreadStatus.CLOSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reply to a closed thread",
            )

        reply = ThreadReply(
            thread_id=thread_id,
            author_id=author.id,
            content=content,
        )
        self.db.add(reply)

        thread.reply_count = (
            self.db.query(func.count(ThreadReply.id))
            .filter(ThreadReply.thread_id == thread_id)
            .scalar()
            or 0
        ) + 1
        thread.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(reply)
        return reply

    def edit_reply(self, reply_id: UUID, user: User, content: str) -> ThreadReply:
        """Edit a reply (author only)."""
        reply = self.db.query(ThreadReply).filter(ThreadReply.id == reply_id).first()
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply not found",
            )
        if reply.author_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can edit this reply",
            )
        reply.content = content
        reply.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(reply)
        return cast(ThreadReply, reply)

    def delete_reply(self, reply_id: UUID, user: User) -> None:
        """Delete a reply (author or admin)."""
        reply = self.db.query(ThreadReply).filter(ThreadReply.id == reply_id).first()
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply not found",
            )
        if reply.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this reply",
            )

        thread_id = reply.thread_id
        self.db.delete(reply)

        # Update reply count
        thread = self._get_thread_or_404(thread_id)
        thread.reply_count = max(0, thread.reply_count - 1)

        self.db.commit()

    def mark_as_solution(self, thread_id: UUID, reply_id: UUID, user: User) -> ThreadReply:
        """Mark a reply as the solution."""
        thread = self._get_thread_or_404(thread_id)
        self._check_author_or_admin(thread, user)

        # Unmark any existing solution
        self.db.query(ThreadReply).filter(
            ThreadReply.thread_id == thread_id,
            ThreadReply.is_solution == True,  # noqa: E712
        ).update({ThreadReply.is_solution: False})

        reply = self._mark_reply_solution(thread_id, reply_id)

        if thread.status == ThreadStatus.OPEN.value:
            thread.status = ThreadStatus.RESOLVED.value
            thread.resolved_by_id = user.id
            thread.resolved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(reply)
        return reply

    def unmark_as_solution(self, thread_id: UUID, reply_id: UUID, user: User) -> ThreadReply:
        """Unmark a reply as solution."""
        thread = self._get_thread_or_404(thread_id)
        self._check_author_or_admin(thread, user)

        reply = (
            self.db.query(ThreadReply)
            .filter(ThreadReply.id == reply_id, ThreadReply.thread_id == thread_id)
            .first()
        )
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply not found in this thread",
            )

        reply.is_solution = False

        if thread.status == ThreadStatus.RESOLVED.value:
            thread.status = ThreadStatus.OPEN.value
            thread.resolved_by_id = None
            thread.resolved_at = None

        self.db.commit()
        self.db.refresh(reply)
        return cast(ThreadReply, reply)

    def _get_thread_or_404(self, thread_id: UUID) -> CommunityThread:
        """Get thread or raise 404."""
        thread = self.db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )
        return cast(CommunityThread, thread)

    def _check_author_or_admin(self, thread: CommunityThread, user: User) -> None:
        """Check if user is author or admin."""
        if thread.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this action",
            )

    def _mark_reply_solution(self, thread_id: UUID, reply_id: UUID) -> ThreadReply:
        """Mark a reply as solution."""
        reply = (
            self.db.query(ThreadReply)
            .filter(ThreadReply.id == reply_id, ThreadReply.thread_id == thread_id)
            .first()
        )
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply not found in this thread",
            )
        reply.is_solution = True
        return cast(ThreadReply, reply)
