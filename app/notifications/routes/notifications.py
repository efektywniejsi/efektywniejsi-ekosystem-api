from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.notifications.models.announcement_log import AnnouncementLog
from app.notifications.models.notification import Notification, NotificationType
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
    db: Session = Depends(get_db),
) -> dict:
    """Send an announcement notification to all active users (admin only)."""
    log = AnnouncementLog(
        subject=request.subject,
        body_html=request.body_html,
        body_text=request.body_text,
        sent_by=current_user.id,
        status="pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    task = send_announcement_notification.delay(
        subject=request.subject,
        body_html=request.body_html,
        body_text=request.body_text,
        announcement_log_id=str(log.id),
    )
    return {"message": "Wysyłka ogłoszenia zlecona", "task_id": task.id}


@router.get("/notifications/announcements")
async def list_announcements(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all announcement logs (admin only)."""
    logs = (
        db.query(AnnouncementLog, User.name)
        .outerjoin(User, AnnouncementLog.sent_by == User.id)
        .order_by(AnnouncementLog.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(log.id),
            "subject": log.subject,
            "sent_by_name": admin_name or "Nieznany",
            "total_recipients": log.total_recipients,
            "sent_count": log.sent_count,
            "skipped_count": log.skipped_count,
            "failed_count": log.failed_count,
            "status": log.status,
            "created_at": log.created_at.isoformat(),
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        }
        for log, admin_name in logs
    ]


@router.get("/notifications/announcements/{announcement_id}/recipients")
async def get_announcement_recipients(
    announcement_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List recipients for a specific announcement (admin only)."""
    log = db.query(AnnouncementLog).filter(AnnouncementLog.id == UUID(announcement_id)).first()
    if not log:
        raise HTTPException(status_code=404, detail="Ogłoszenie nie znalezione")

    rows = (
        db.query(Notification, User.name, User.email)
        .join(User, Notification.user_id == User.id)
        .filter(Notification.announcement_log_id == UUID(announcement_id))
        .order_by(Notification.created_at.desc())
        .all()
    )

    # Fallback for notifications created before announcement_log_id existed
    if not rows and log.completed_at:
        rows = (
            db.query(Notification, User.name, User.email)
            .join(User, Notification.user_id == User.id)
            .filter(
                and_(
                    Notification.notification_type == NotificationType.ANNOUNCEMENT.value,
                    Notification.subject == log.subject,
                    Notification.created_at >= log.created_at,
                    Notification.created_at <= log.completed_at,
                )
            )
            .order_by(Notification.created_at.desc())
            .all()
        )

    return [
        {
            "user_name": user_name or "Nieznany",
            "user_email": user_email,
            "status": notification.status,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            "error_message": notification.error_message,
        }
        for notification, user_name, user_email in rows
    ]
