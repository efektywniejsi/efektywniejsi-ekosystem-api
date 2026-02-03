"""Celery tasks for sending notifications."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.auth.models.user import User
from app.auth.services.email_service import get_email_service
from app.core.celery_app import celery_app
from app.core.config import settings
from app.courses.models.course import Course
from app.courses.models.enrollment import Enrollment
from app.db.session import SessionLocal
from app.notifications.email_templates import (
    build_announcement_email,
    build_course_update_email,
    build_direct_message_email,
)
from app.notifications.models.announcement_log import AnnouncementLog
from app.notifications.models.notification import Notification, NotificationStatus, NotificationType

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_course_update_notification(
    self: Any,
    course_id: str,
    update_type: str,
    item_title: str,
) -> dict[str, int]:
    """Send course update notifications to all enrolled users."""
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == UUID(course_id)).first()
        if not course:
            logger.error("Course %s not found, skipping notification", course_id)
            return {"sent": 0, "skipped": 0}

        enrolled_user_ids = [
            row.user_id
            for row in db.query(Enrollment.user_id)
            .filter(Enrollment.course_id == UUID(course_id))
            .all()
        ]
        if not enrolled_user_ids:
            logger.info("No enrolled users for course %s", course_id)
            return {"sent": 0, "skipped": 0}

        users = (
            db.query(User).filter(User.id.in_(enrolled_user_ids), User.is_active == True).all()  # noqa: E712
        )

        email_service = get_email_service()
        sent = 0
        skipped = 0

        for user in users:
            prefs = user.notification_preferences or {}
            if not prefs.get("course_updates", True):
                skipped += 1
                continue

            email_msg = build_course_update_email(
                user_name=user.name,
                user_email=user.email,
                course_title=course.title,
                course_slug=course.slug,
                update_type=update_type,
                item_title=item_title,
            )

            notification = Notification(
                user_id=user.id,
                notification_type=NotificationType.COURSE_UPDATE.value,
                subject=email_msg.subject,
                status=NotificationStatus.PENDING.value,
                course_id=course.id,
            )
            db.add(notification)

            try:
                success = asyncio.run(email_service.send_email(email_msg))
                if success:
                    notification.status = NotificationStatus.SENT.value
                    notification.sent_at = datetime.now(UTC)
                    sent += 1
                else:
                    notification.status = NotificationStatus.FAILED.value
                    notification.error_message = "Email service returned False"
                    skipped += 1
            except Exception as exc:
                notification.status = NotificationStatus.FAILED.value
                notification.error_message = str(exc)[:500]
                skipped += 1
                logger.exception("Failed to send course update email to %s", user.email)

            db.commit()

        logger.info(
            "Course update notifications for %s: sent=%d, skipped=%d",
            course_id,
            sent,
            skipped,
        )
        return {"sent": sent, "skipped": skipped}
    except Exception as exc:
        logger.exception("send_course_update_notification failed: %s", exc)
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_announcement_notification(
    self: Any,
    subject: str,
    body_html: str,
    body_text: str,
    announcement_log_id: str | None = None,
) -> dict[str, int]:
    """Send an announcement email to all active users who opted in."""
    db = SessionLocal()
    try:
        log: AnnouncementLog | None = None
        if announcement_log_id:
            log = (
                db.query(AnnouncementLog)
                .filter(AnnouncementLog.id == UUID(announcement_log_id))
                .first()
            )
            if log:
                log.status = "in_progress"
                db.commit()

        users = db.query(User).filter(User.is_active == True).all()  # noqa: E712

        if log:
            log.total_recipients = len(users)
            db.commit()

        email_service = get_email_service()
        sent = 0
        skipped = 0
        failed = 0

        for user in users:
            prefs = user.notification_preferences or {}
            if not prefs.get("admin_announcements", True):
                skipped += 1
                continue

            email_msg = build_announcement_email(
                user_name=user.name,
                user_email=user.email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )

            notification = Notification(
                user_id=user.id,
                notification_type=NotificationType.ANNOUNCEMENT.value,
                subject=subject,
                status=NotificationStatus.PENDING.value,
                announcement_log_id=UUID(announcement_log_id) if announcement_log_id else None,
            )
            db.add(notification)

            try:
                success = asyncio.run(email_service.send_email(email_msg))
                if success:
                    notification.status = NotificationStatus.SENT.value
                    notification.sent_at = datetime.now(UTC)
                    sent += 1
                else:
                    notification.status = NotificationStatus.FAILED.value
                    notification.error_message = "Email service returned False"
                    failed += 1
            except Exception as exc:
                notification.status = NotificationStatus.FAILED.value
                notification.error_message = str(exc)[:500]
                failed += 1
                logger.exception("Failed to send announcement email to %s", user.email)

            db.commit()

        if log:
            log.sent_count = sent
            log.skipped_count = skipped
            log.failed_count = failed
            log.status = "completed"
            log.completed_at = datetime.now(UTC)
            db.commit()

        logger.info(
            "Announcement notifications: sent=%d, skipped=%d, failed=%d", sent, skipped, failed
        )
        return {"sent": sent, "skipped": skipped, "failed": failed}
    except Exception as exc:
        logger.exception("send_announcement_notification failed: %s", exc)
        if log:
            try:
                log.status = "failed"
                db.commit()
            except Exception:
                db.rollback()
        else:
            db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_direct_message_notification(
    self: Any,
    recipient_user_id: str,
    sender_user_id: str,
    message_preview: str,
    conversation_id: str,
) -> dict[str, str]:
    """Send an email notification for a new direct message."""
    db = SessionLocal()
    try:
        recipient = db.query(User).filter(User.id == UUID(recipient_user_id)).first()
        sender = db.query(User).filter(User.id == UUID(sender_user_id)).first()

        if not recipient or not sender:
            logger.error(
                "User not found: recipient=%s, sender=%s", recipient_user_id, sender_user_id
            )
            return {"status": "skipped", "reason": "user_not_found"}

        prefs = recipient.notification_preferences or {}
        if not prefs.get("direct_messages", True):
            logger.info("User %s opted out of DM notifications", recipient_user_id)
            return {"status": "skipped", "reason": "opted_out"}

        conversation_url = f"{settings.FRONTEND_URL}/wiadomosci/{conversation_id}"

        email_msg = build_direct_message_email(
            user_name=recipient.name,
            user_email=recipient.email,
            sender_name=sender.name,
            message_preview=message_preview,
            conversation_url=conversation_url,
        )

        notification = Notification(
            user_id=recipient.id,
            notification_type=NotificationType.DIRECT_MESSAGE.value,
            subject=email_msg.subject,
            status=NotificationStatus.PENDING.value,
        )
        db.add(notification)

        try:
            email_service = get_email_service()
            success = asyncio.run(email_service.send_email(email_msg))
            if success:
                notification.status = NotificationStatus.SENT.value
                notification.sent_at = datetime.now(UTC)
                db.commit()
                return {"status": "sent"}
            else:
                notification.status = NotificationStatus.FAILED.value
                notification.error_message = "Email service returned False"
                db.commit()
                return {"status": "failed", "reason": "email_service_false"}
        except Exception as exc:
            notification.status = NotificationStatus.FAILED.value
            notification.error_message = str(exc)[:500]
            db.commit()
            logger.exception("Failed to send DM email to %s", recipient.email)
            return {"status": "failed", "reason": str(exc)[:200]}
    except Exception as exc:
        logger.exception("send_direct_message_notification failed: %s", exc)
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
    finally:
        db.close()
