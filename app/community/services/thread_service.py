import logging
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
from app.community.models.reply import ThreadReply
from app.community.models.thread import CommunityThread, ThreadStatus
from app.community.models.thread_tag import ThreadTag, ThreadTagAssociation
from app.community.schemas.thread import (
    AdminStatsResponse,
    AdminThreadUpdate,
    AuthorInfo,
    BulkActionResponse,
    ReplyResponse,
    ThreadAttachmentResponse,
    ThreadCreate,
    ThreadDetailResponse,
    ThreadListItem,
    ThreadListResponse,
    ThreadUpdate,
    TopAuthorItem,
    UserActivityItem,
    UserActivityResponse,
)

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
        self.db.flush()

        if data.tags:
            tag_names = [t.strip().lower()[:30] for t in data.tags[:5] if t.strip()]
            for tag_name in tag_names:
                tag = self.db.query(ThreadTag).filter(ThreadTag.name == tag_name).first()
                if not tag:
                    tag = ThreadTag(name=tag_name)
                    self.db.add(tag)
                    self.db.flush()
                self.db.add(ThreadTagAssociation(thread_id=thread.id, tag_id=tag.id))

        self.db.commit()
        self.db.refresh(thread)
        return thread

    def get_popular_tags(self, limit: int = 20) -> list[str]:
        rows = (
            self.db.query(ThreadTag.name, func.count(ThreadTagAssociation.thread_id).label("cnt"))
            .join(ThreadTagAssociation, ThreadTag.id == ThreadTagAssociation.tag_id)
            .group_by(ThreadTag.name)
            .order_by(func.count(ThreadTagAssociation.thread_id).desc())
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows]

    def get_category_counts(self) -> dict[str, int]:
        rows = (
            self.db.query(CommunityThread.category, func.count(CommunityThread.id))
            .group_by(CommunityThread.category)
            .all()
        )
        return {str(category): int(count) for category, count in rows}

    def get_all_threads(
        self,
        category: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> ThreadListResponse:
        # Subquery: last reply date per thread (avoids N+1)
        last_reply_sub = (
            self.db.query(
                ThreadReply.thread_id,
                func.max(ThreadReply.created_at).label("last_reply_at"),
            )
            .group_by(ThreadReply.thread_id)
            .subquery()
        )

        query = (
            self.db.query(CommunityThread, last_reply_sub.c.last_reply_at)
            .options(joinedload(CommunityThread.author))
            .outerjoin(last_reply_sub, last_reply_sub.c.thread_id == CommunityThread.id)
        )

        if category:
            query = query.filter(CommunityThread.category == category)
        if status_filter:
            query = query.filter(CommunityThread.status == status_filter)
        if search:
            query = query.filter(CommunityThread.title.ilike(f"%{_escape_like(search)}%"))

        total = query.count()
        rows = (
            query.order_by(
                CommunityThread.is_pinned.desc(),
                CommunityThread.updated_at.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        items = [
            ThreadListItem(
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
                last_activity=last_reply_at if last_reply_at else thread.created_at,
                course_title=thread.course.title if thread.course else None,
                module_title=thread.module.title if thread.module else None,
                lesson_title=thread.lesson.title if thread.lesson else None,
                tags=[tag.name for tag in thread.tags] if thread.tags else [],
            )
            for thread, last_reply_at in rows
        ]
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
                detail="Wątek nie znaleziony",
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
                detail="Nie można odpowiadać w zamkniętym wątku",
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
        thread.updated_at = datetime.now(UTC)

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
        thread.resolved_at = datetime.now(UTC)

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
            ThreadReply.is_solution == True,  # noqa: E712
        ).update({ThreadReply.is_solution: False})

        reply = self._mark_reply_solution(thread_id, reply_id)

        if thread.status == ThreadStatus.OPEN.value:
            thread.status = ThreadStatus.RESOLVED.value
            thread.resolved_by_id = user.id
            thread.resolved_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(reply)
        return reply

    def unmark_reply_as_solution(self, thread_id: UUID, reply_id: UUID, user: User) -> ThreadReply:
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
                detail="Odpowiedź nie znaleziona w tym wątku",
            )

        reply.is_solution = False

        if thread.status == ThreadStatus.RESOLVED.value:
            thread.status = ThreadStatus.OPEN.value
            thread.resolved_by_id = None
            thread.resolved_at = None

        self.db.commit()
        self.db.refresh(reply)
        return cast(ThreadReply, reply)

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
                detail="Odpowiedź nie znaleziona",
            )
        if reply.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Brak uprawnień do usunięcia tej odpowiedzi",
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
                detail="Tylko autor może edytować ten wątek",
            )
        thread.title = data.title
        thread.content = data.content

        if data.clear_course_context:
            thread.course_id = None
            thread.module_id = None
            thread.lesson_id = None
        else:
            if data.course_id is not None:
                thread.course_id = data.course_id
            if data.module_id is not None:
                thread.module_id = data.module_id
            if data.lesson_id is not None:
                thread.lesson_id = data.lesson_id

        thread.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def edit_reply(self, reply_id: UUID, user: User, content: str) -> ThreadReply:
        reply = self.db.query(ThreadReply).filter(ThreadReply.id == reply_id).first()
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Odpowiedź nie znaleziona",
            )
        if reply.author_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tylko autor może edytować tę odpowiedź",
            )
        reply.content = content
        reply.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(reply)
        return cast(ThreadReply, reply)

    def close_thread(self, thread_id: UUID) -> CommunityThread:
        thread = self._get_thread_or_404(thread_id)
        thread.status = ThreadStatus.CLOSED.value
        thread.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def reopen_thread(self, thread_id: UUID) -> CommunityThread:
        thread = self._get_thread_or_404(thread_id)
        thread.status = ThreadStatus.OPEN.value
        thread.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def move_thread_category(self, thread_id: UUID, category: str) -> CommunityThread:
        thread = self._get_thread_or_404(thread_id)
        thread.category = category
        thread.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def admin_edit_thread(self, thread_id: UUID, data: AdminThreadUpdate) -> CommunityThread:
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
        thread.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def bulk_action(self, thread_ids: list[UUID], action: str) -> BulkActionResponse:
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

    def get_admin_statistics(self) -> AdminStatsResponse:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

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

        category_counts = self.get_category_counts()

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
            course_id=thread.course_id,
            module_id=thread.module_id,
            lesson_id=thread.lesson_id,
            course_title=thread.course.title if thread.course else None,
            module_title=thread.module.title if thread.module else None,
            lesson_title=thread.lesson.title if thread.lesson else None,
            tags=[tag.name for tag in thread.tags] if thread.tags else [],
            attachments=[
                ThreadAttachmentResponse(
                    id=a.id,
                    file_name=a.file_name,
                    file_size_bytes=a.file_size_bytes,
                    mime_type=a.mime_type,
                    created_at=a.created_at,
                )
                for a in (thread.attachments or [])
            ],
        )

    def _get_thread_or_404(self, thread_id: UUID) -> CommunityThread:
        thread = self.db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wątek nie znaleziony",
            )
        return cast(CommunityThread, thread)

    def _check_author_or_admin(self, thread: CommunityThread, user: User) -> None:
        if thread.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Brak uprawnień do tej operacji",
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
                detail="Odpowiedź nie znaleziona w tym wątku",
            )
        reply.is_solution = True
        return cast(ThreadReply, reply)

    @staticmethod
    def _build_author(user: User) -> AuthorInfo:
        return AuthorInfo(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
        )
