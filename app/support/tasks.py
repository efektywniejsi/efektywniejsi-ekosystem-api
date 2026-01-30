"""Celery tasks for support ticket notifications."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.auth.models.user import User
from app.auth.services.email_service import get_email_service
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.support.models.ticket import SupportTicket
from app.support.services.notification_service import build_admin_reply_email

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_ticket_reply_notification(
    self: Any,
    ticket_id: str,
    reply_preview: str,
) -> dict[str, str]:
    """Send email notification when admin replies to a support ticket."""
    db = SessionLocal()
    try:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == UUID(ticket_id)).first()
        if not ticket:
            logger.error("Ticket %s not found, skipping notification", ticket_id)
            return {"status": "skipped", "reason": "ticket_not_found"}

        user = db.query(User).filter(User.id == ticket.user_id).first()
        if not user:
            logger.error("User for ticket %s not found", ticket_id)
            return {"status": "skipped", "reason": "user_not_found"}

        email_msg = build_admin_reply_email(
            user_name=user.name,
            user_email=user.email,
            ticket_subject=ticket.subject,
            reply_preview=reply_preview,
        )

        email_service = get_email_service()
        success = asyncio.run(email_service.send_email(email_msg))

        if success:
            logger.info("Ticket reply notification sent to %s", user.email)
            return {"status": "sent"}

        logger.warning("Email service returned False for ticket %s", ticket_id)
        return {"status": "failed", "reason": "email_service_returned_false"}
    except Exception as exc:
        logger.exception("send_ticket_reply_notification failed: %s", exc)
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
    finally:
        db.close()
