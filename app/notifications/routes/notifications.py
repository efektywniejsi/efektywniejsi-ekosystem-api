from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.notifications.tasks import send_announcement_notification

router = APIRouter()


class AnnouncementRequest(BaseModel):
    subject: str
    body_html: str
    body_text: str


@router.post(
    "/notifications/announcement",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_announcement(
    request: AnnouncementRequest,
    current_user: User = Depends(require_admin),
) -> dict:
    """Send an announcement notification to all active users (admin only)."""
    task = send_announcement_notification.delay(
        subject=request.subject,
        body_html=request.body_html,
        body_text=request.body_text,
    )
    return {"message": "Wysyłka ogłoszenia zlecona", "task_id": task.id}
