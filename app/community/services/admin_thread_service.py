"""Admin operations service for community threads."""

import logging
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.community.models.reply import ThreadReply
from app.community.models.thread import CommunityThread, ThreadStatus
from app.community.schemas.thread import (
    AdminStatsResponse,
    AdminThreadUpdate,
    BulkActionResponse,
    TopAuthorItem,
    UserActivityItem,
    UserActivityResponse,
)

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AdminThreadService:
    """Service for admin thread operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def pin_thread(self, thread_id: UUID) -> CommunityThread:
        """Toggle thread pin status."""
        thread = self._get_thread_or_404(thread_id)
        thread.is_pinned = not thread.is_pinned
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def delete_thread(self, thread_id: UUID) -> None:
        """Delete a thread."""
        thread = self._get_thread_or_404(thread_id)
        self.db.delete(thread)
        self.db.commit()

    def close_thread(self, thread_id: UUID) -> CommunityThread:
        """Close a thread."""
        thread = self._get_thread_or_404(thread_id)
        thread.status = ThreadStatus.CLOSED.value
        thread.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def reopen_thread(self, thread_id: UUID) -> CommunityThread:
        """Reopen a thread."""
        thread = self._get_thread_or_404(thread_id)
        thread.status = ThreadStatus.OPEN.value
        thread.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def move_thread_category(self, thread_id: UUID, category: str) -> CommunityThread:
        """Move thread to different category."""
        thread = self._get_thread_or_404(thread_id)
        thread.category = category
        thread.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def edit_thread(self, thread_id: UUID, data: AdminThreadUpdate) -> CommunityThread:
        """Edit thread as admin."""
        thread = self._get_thread_or_404(thread_id)
        if data.title is not None:
            thread.title = data.title
        if data.content is not None:
            thread.content = data.content
        if data.category is not None:
            cat = data.category
            thread.category = cat.value if hasattr(cat, "value") else cat
        if data.is_pinned is not None:
            thread.is_pinned = data.is_pinned
        thread.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def bulk_action(self, thread_ids: list[UUID], action: str) -> BulkActionResponse:
        """Perform bulk action on threads."""
        threads = self.db.query(CommunityThread).filter(CommunityThread.id.in_(thread_ids)).all()
        affected = 0
        for thread in threads:
            if action == "close":
                thread.status = ThreadStatus.CLOSED.value
            elif action == "reopen":
                thread.status = ThreadStatus.OPEN.value
            elif action == "delete":
                self.db.delete(thread)
            elif action == "pin":
                thread.is_pinned = True
            elif action == "unpin":
                thread.is_pinned = False
            else:
                continue
            affected += 1
        self.db.commit()
        return BulkActionResponse(affected=affected, action=action)

    def get_statistics(self) -> AdminStatsResponse:
        """Get admin statistics for community."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        total = self.db.query(func.count(CommunityThread.id)).scalar() or 0
        open_count = (
            self.db.query(func.count(CommunityThread.id))
            .filter(CommunityThread.status == ThreadStatus.OPEN.value)
            .scalar()
            or 0
        )
        resolved_count = (
            self.db.query(func.count(CommunityThread.id))
            .filter(CommunityThread.status == ThreadStatus.RESOLVED.value)
            .scalar()
            or 0
        )
        closed_count = (
            self.db.query(func.count(CommunityThread.id))
            .filter(CommunityThread.status == ThreadStatus.CLOSED.value)
            .scalar()
            or 0
        )
        total_replies = self.db.query(func.count(ThreadReply.id)).scalar() or 0
        threads_today = (
            self.db.query(func.count(CommunityThread.id))
            .filter(CommunityThread.created_at >= today_start)
            .scalar()
            or 0
        )
        replies_today = (
            self.db.query(func.count(ThreadReply.id))
            .filter(ThreadReply.created_at >= today_start)
            .scalar()
            or 0
        )

        rows = (
            self.db.query(CommunityThread.category, func.count(CommunityThread.id))
            .group_by(CommunityThread.category)
            .all()
        )
        category_counts = {str(category): int(count) for category, count in rows}

        top_authors_rows = (
            self.db.query(
                User.id,
                User.name,
                func.count(CommunityThread.id).label("thread_count"),
            )
            .join(CommunityThread, CommunityThread.author_id == User.id)
            .group_by(User.id, User.name)
            .order_by(func.count(CommunityThread.id).desc())
            .limit(10)
            .all()
        )
        top_authors = [
            TopAuthorItem(id=str(row[0]), name=row[1], thread_count=row[2])
            for row in top_authors_rows
        ]

        return AdminStatsResponse(
            total_threads=total,
            open_threads=open_count,
            resolved_threads=resolved_count,
            closed_threads=closed_count,
            total_replies=total_replies,
            threads_today=threads_today,
            replies_today=replies_today,
            category_counts=category_counts,
            top_authors=top_authors,
        )

    def get_user_activity(
        self, page: int = 1, limit: int = 20, search: str | None = None
    ) -> UserActivityResponse:
        """Get user activity for admin view."""
        thread_count_sub = (
            self.db.query(
                CommunityThread.author_id,
                func.count(CommunityThread.id).label("thread_count"),
                func.max(CommunityThread.created_at).label("last_thread"),
            )
            .group_by(CommunityThread.author_id)
            .subquery()
        )
        reply_count_sub = (
            self.db.query(
                ThreadReply.author_id,
                func.count(ThreadReply.id).label("reply_count"),
                func.count(case((ThreadReply.is_solution == True, 1))).label("solution_count"),  # noqa: E712
                func.max(ThreadReply.created_at).label("last_reply"),
            )
            .group_by(ThreadReply.author_id)
            .subquery()
        )

        query = (
            self.db.query(
                User.id,
                User.name,
                func.coalesce(thread_count_sub.c.thread_count, 0).label("thread_count"),
                func.coalesce(reply_count_sub.c.reply_count, 0).label("reply_count"),
                func.coalesce(reply_count_sub.c.solution_count, 0).label("solution_count"),
                func.greatest(
                    thread_count_sub.c.last_thread,
                    reply_count_sub.c.last_reply,
                ).label("last_activity"),
            )
            .outerjoin(thread_count_sub, thread_count_sub.c.author_id == User.id)
            .outerjoin(reply_count_sub, reply_count_sub.c.author_id == User.id)
            .filter((thread_count_sub.c.thread_count > 0) | (reply_count_sub.c.reply_count > 0))
        )

        if search:
            query = query.filter(User.name.ilike(f"%{_escape_like(search)}%"))

        total = query.count()
        rows = (
            query.order_by(func.coalesce(thread_count_sub.c.thread_count, 0).desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        users = [
            UserActivityItem(
                user_id=row[0],
                user_name=row[1],
                thread_count=row[2],
                reply_count=row[3],
                solution_count=row[4],
                last_activity=row[5],
            )
            for row in rows
        ]

        return UserActivityResponse(users=users, total=total)

    def _get_thread_or_404(self, thread_id: UUID) -> CommunityThread:
        """Get thread or raise 404."""
        thread = self.db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )
        return cast(CommunityThread, thread)
