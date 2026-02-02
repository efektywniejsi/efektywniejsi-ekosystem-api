from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.community.schemas.public_profile import PublicProfileResponse
from app.community.schemas.thread import (
    ReplyCreate,
    ReplyResponse,
    ReplyUpdate,
    ThreadCreate,
    ThreadDetailResponse,
    ThreadListResponse,
    ThreadUpdate,
)
from app.community.services.public_profile_service import PublicProfileService
from app.community.services.thread_service import ThreadService
from app.db.session import get_db

router = APIRouter()


@router.get("/users/{user_id}/profile", response_model=PublicProfileResponse)
def get_user_public_profile(
    user_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PublicProfileResponse:
    service = PublicProfileService(db)
    return service.get_public_profile(user_id)


@router.post("/threads", response_model=ThreadDetailResponse, status_code=201)
def create_thread(
    data: ThreadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    thread = service.create_thread(current_user, data)
    reloaded = service.get_thread_detail(thread.id)
    return service.build_detail_response(reloaded)


@router.get("/threads/tags/popular")
def get_popular_tags(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    service = ThreadService(db)
    return service.get_popular_tags()


@router.get("/threads/counts")
def get_thread_counts(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    service = ThreadService(db)
    return service.get_category_counts()


@router.get("/threads", response_model=ThreadListResponse)
def get_threads(
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThreadListResponse:
    service = ThreadService(db)
    return service.get_all_threads(
        category=category,
        status_filter=status,
        search=search,
        page=page,
        limit=limit,
    )


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.post("/threads/{thread_id}/view", status_code=204)
def track_thread_view(
    thread_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = ThreadService(db)
    service.increment_view_count(thread_id)


@router.patch("/threads/{thread_id}", response_model=ThreadDetailResponse)
def edit_thread(
    thread_id: UUID,
    data: ThreadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.edit_thread(thread_id, current_user, data)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.post(
    "/threads/{thread_id}/replies",
    response_model=ReplyResponse,
    status_code=201,
)
def add_reply(
    thread_id: UUID,
    data: ReplyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyResponse:
    service = ThreadService(db)
    reply = service.add_reply(thread_id, current_user, data.content)
    return ReplyResponse(
        id=reply.id,
        thread_id=reply.thread_id,
        author={
            "id": current_user.id,
            "name": current_user.name,
            "avatar_url": current_user.avatar_url,
        },
        content=reply.content,
        is_solution=reply.is_solution,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


@router.patch("/replies/{reply_id}", response_model=ReplyResponse)
def edit_reply(
    reply_id: UUID,
    data: ReplyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyResponse:
    service = ThreadService(db)
    reply = service.edit_reply(reply_id, current_user, data.content)
    return ReplyResponse(
        id=reply.id,
        thread_id=reply.thread_id,
        author={
            "id": reply.author.id,
            "name": reply.author.name,
            "avatar_url": reply.author.avatar_url,
        },
        content=reply.content,
        is_solution=reply.is_solution,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


@router.patch(
    "/threads/{thread_id}/resolve",
    response_model=ThreadDetailResponse,
)
def resolve_thread(
    thread_id: UUID,
    solution_reply_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.mark_as_resolved(thread_id, current_user, solution_reply_id)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.patch(
    "/threads/{thread_id}/replies/{reply_id}/solution",
    response_model=ReplyResponse,
)
def mark_solution(
    thread_id: UUID,
    reply_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyResponse:
    service = ThreadService(db)
    reply = service.mark_reply_as_solution(thread_id, reply_id, current_user)
    return ReplyResponse(
        id=reply.id,
        thread_id=reply.thread_id,
        author={
            "id": reply.author.id,
            "name": reply.author.name,
            "avatar_url": reply.author.avatar_url,
        },
        content=reply.content,
        is_solution=reply.is_solution,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


@router.delete(
    "/threads/{thread_id}/replies/{reply_id}/solution",
    response_model=ReplyResponse,
)
def unmark_solution(
    thread_id: UUID,
    reply_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyResponse:
    service = ThreadService(db)
    reply = service.unmark_reply_as_solution(thread_id, reply_id, current_user)
    return ReplyResponse(
        id=reply.id,
        thread_id=reply.thread_id,
        author={
            "id": reply.author.id,
            "name": reply.author.name,
            "avatar_url": reply.author.avatar_url,
        },
        content=reply.content,
        is_solution=reply.is_solution,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )
