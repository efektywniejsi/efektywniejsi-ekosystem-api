from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.community.schemas.thread import ThreadDetailResponse
from app.community.services.thread_service import ThreadService
from app.db.session import get_db

router = APIRouter()


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
