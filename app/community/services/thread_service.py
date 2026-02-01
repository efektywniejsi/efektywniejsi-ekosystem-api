import logging
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
from app.community.models.reply import ThreadReply
from app.community.models.thread import CommunityThread, ThreadStatus
from app.community.schemas.thread import (
    AuthorInfo,
    ReplyResponse,
    ThreadCreate,
    ThreadDetailResponse,
    ThreadListItem,
    ThreadListResponse,
    ThreadUpdate,
)

logger = logging.getLogger(__name__)


class ThreadService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_thread(self, user: User, data: ThreadCreate) -> CommunityThread:
        thread = CommunityThread(
            author_id=user.id,
            title=data.title,
            content=data.content,
            category=data.category.value,
            course_id=data.course_id,
            module_id=data.module_id,
            lesson_id=data.lesson_id,
        )
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def get_category_counts(self) -> dict[str, int]:
        rows = (
            self.db.query(CommunityThread.category, func.count(CommunityThread.id))
            .group_by(CommunityThread.category)
            .all()
        )
        return dict(rows)

    def get_all_threads(
        self,
        category: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> ThreadListResponse:
        query = self.db.query(CommunityThread).options(joinedload(CommunityThread.author))

        if category:
            query = query.filter(CommunityThread.category == category)
        if status_filter:
            query = query.filter(CommunityThread.status == status_filter)
        if search:
            query = query.filter(CommunityThread.title.ilike(f"%{search}%"))

        total = query.count()
        threads = (
            query.order_by(
                CommunityThread.is_pinned.desc(),
                CommunityThread.updated_at.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        items = [self._build_list_item(t) for t in threads]
        return ThreadListResponse(threads=items, total=total)

    def get_thread_detail(self, thread_id: UUID) -> CommunityThread:
        thread: CommunityThread | None = (
            self.db.query(CommunityThread)
            .options(
                joinedload(CommunityThread.replies).joinedload(ThreadReply.author),
                joinedload(CommunityThread.author),
                joinedload(CommunityThread.resolved_by),
            )
            .filter(CommunityThread.id == thread_id)
            .first()
        )
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )
        return thread

    def increment_view_count(self, thread_id: UUID) -> None:
        self.db.query(CommunityThread).filter(CommunityThread.id == thread_id).update(
            {CommunityThread.view_count: CommunityThread.view_count + 1}
        )
        self.db.commit()

    def add_reply(self, thread_id: UUID, author: User, content: str) -> ThreadReply:
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

    def mark_as_resolved(
        self, thread_id: UUID, user: User, solution_reply_id: UUID | None = None
    ) -> CommunityThread:
        thread = self._get_thread_or_404(thread_id)
        self._check_author_or_admin(thread, user)

        thread.status = ThreadStatus.RESOLVED.value
        thread.resolved_by_id = user.id
        thread.resolved_at = datetime.utcnow()

        if solution_reply_id:
            self._mark_reply_solution(thread_id, solution_reply_id)

        self.db.commit()
        self.db.refresh(thread)
        return thread

    def mark_reply_as_solution(self, thread_id: UUID, reply_id: UUID, user: User) -> ThreadReply:
        thread = self._get_thread_or_404(thread_id)
        self._check_author_or_admin(thread, user)

        # Unmark any existing solution
        self.db.query(ThreadReply).filter(
            ThreadReply.thread_id == thread_id,
            ThreadReply.is_solution.is_(True),
        ).update({ThreadReply.is_solution: False})

        reply = self._mark_reply_solution(thread_id, reply_id)

        if thread.status == ThreadStatus.OPEN.value:
            thread.status = ThreadStatus.RESOLVED.value
            thread.resolved_by_id = user.id
            thread.resolved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(reply)
        return reply

    def pin_thread(self, thread_id: UUID) -> CommunityThread:
        thread = self._get_thread_or_404(thread_id)
        thread.is_pinned = not thread.is_pinned
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def delete_thread(self, thread_id: UUID) -> None:
        thread = self._get_thread_or_404(thread_id)
        self.db.delete(thread)
        self.db.commit()

    def delete_reply(self, reply_id: UUID, user: User) -> None:
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

    def edit_thread(self, thread_id: UUID, user: User, data: ThreadUpdate) -> CommunityThread:
        thread = self._get_thread_or_404(thread_id)
        if thread.author_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can edit this thread",
            )
        thread.title = data.title
        thread.content = data.content
        thread.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def edit_reply(self, reply_id: UUID, user: User, content: str) -> ThreadReply:
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

    def build_detail_response(self, thread: CommunityThread) -> ThreadDetailResponse:
        return ThreadDetailResponse(
            id=thread.id,
            title=thread.title,
            content=thread.content,
            status=thread.status,
            category=thread.category,
            is_pinned=thread.is_pinned,
            reply_count=thread.reply_count,
            view_count=thread.view_count,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            author=self._build_author(thread.author),
            resolved_by=self._build_author(thread.resolved_by) if thread.resolved_by else None,
            resolved_at=thread.resolved_at,
            replies=[
                ReplyResponse(
                    id=r.id,
                    thread_id=r.thread_id,
                    author=self._build_author(r.author),
                    content=r.content,
                    is_solution=r.is_solution,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in thread.replies
            ],
            course_title=thread.course.title if thread.course else None,
            module_title=thread.module.title if thread.module else None,
            lesson_title=thread.lesson.title if thread.lesson else None,
        )

    def _get_thread_or_404(self, thread_id: UUID) -> CommunityThread:
        thread = self.db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )
        return cast(CommunityThread, thread)

    def _check_author_or_admin(self, thread: CommunityThread, user: User) -> None:
        if thread.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this action",
            )

    def _mark_reply_solution(self, thread_id: UUID, reply_id: UUID) -> ThreadReply:
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

    def _build_list_item(self, thread: CommunityThread) -> ThreadListItem:
        last_reply = (
            self.db.query(ThreadReply.created_at)
            .filter(ThreadReply.thread_id == thread.id)
            .order_by(ThreadReply.created_at.desc())
            .first()
        )
        last_activity = last_reply[0] if last_reply else thread.created_at

        return ThreadListItem(
            id=thread.id,
            title=thread.title,
            status=thread.status,
            category=thread.category,
            is_pinned=thread.is_pinned,
            reply_count=thread.reply_count,
            view_count=thread.view_count,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            author=self._build_author(thread.author),
            last_activity=last_activity,
            course_title=thread.course.title if thread.course else None,
            module_title=thread.module.title if thread.module else None,
            lesson_title=thread.lesson.title if thread.lesson else None,
        )

    @staticmethod
    def _build_author(user: User) -> AuthorInfo:
        return AuthorInfo(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
        )
