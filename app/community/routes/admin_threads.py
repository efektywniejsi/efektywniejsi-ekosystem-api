from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.community.schemas.thread import (
    AdminStatsResponse,
    AdminThreadUpdate,
    BulkActionRequest,
    BulkActionResponse,
    ThreadDetailResponse,
    ThreadMoveRequest,
    UserActivityResponse,
)
from app.community.services.thread_service import ThreadService
from app.db.session import get_db

router = APIRouter()


@router.get("/community/stats", response_model=AdminStatsResponse)
def get_community_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminStatsResponse:
    service = ThreadService(db)
    return service.get_admin_statistics()


@router.get("/community/user-activity", response_model=UserActivityResponse)
def get_user_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserActivityResponse:
    service = ThreadService(db)
    return service.get_user_activity(page=page, limit=limit, search=search)


@router.patch(
    "/community/threads/{thread_id}/pin",
    response_model=ThreadDetailResponse,
)
def toggle_pin(
    thread_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.pin_thread(thread_id)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.patch(
    "/community/threads/{thread_id}/close",
    response_model=ThreadDetailResponse,
)
def close_thread(
    thread_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.close_thread(thread_id)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.patch(
    "/community/threads/{thread_id}/reopen",
    response_model=ThreadDetailResponse,
)
def reopen_thread(
    thread_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.reopen_thread(thread_id)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.patch(
    "/community/threads/{thread_id}/move",
    response_model=ThreadDetailResponse,
)
def move_thread(
    thread_id: UUID,
    data: ThreadMoveRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.move_thread_category(thread_id, data.category.value)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.patch(
    "/community/threads/{thread_id}/admin-edit",
    response_model=ThreadDetailResponse,
)
def admin_edit_thread(
    thread_id: UUID,
    data: AdminThreadUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    service = ThreadService(db)
    service.admin_edit_thread(thread_id, data)
    thread = service.get_thread_detail(thread_id)
    return service.build_detail_response(thread)


@router.post("/community/bulk", response_model=BulkActionResponse)
def bulk_action(
    data: BulkActionRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BulkActionResponse:
    service = ThreadService(db)
    return service.bulk_action(data.thread_ids, data.action)


@router.delete("/community/threads/{thread_id}", status_code=204)
def admin_delete_thread(
    thread_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    service = ThreadService(db)
    service.delete_thread(thread_id)


@router.delete("/community/replies/{reply_id}", status_code=204)
def admin_delete_reply(
    reply_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    service = ThreadService(db)
    service.delete_reply(reply_id, admin)
