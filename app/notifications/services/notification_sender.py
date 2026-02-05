"""Notification sender service with common logic for email notifications.

This module provides a reusable component for sending notifications
that handles user preferences, notification creation, and email delivery.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.auth.services.email_service import EmailMessage, get_email_service
from app.notifications.models.notification import Notification, NotificationStatus, NotificationType

logger = logging.getLogger(__name__)


@dataclass
class NotificationContext:
    """Context for creating a notification."""

    user: User
    notification_type: NotificationType
    subject: str
    email_message: EmailMessage
    course_id: UUID | None = None
    announcement_log_id: UUID | None = None


@dataclass
class SendResult:
    """Result of sending a notification."""

    sent: bool
    skipped: bool = False
    failed: bool = False
    reason: str | None = None


class NotificationSender:
    """Service for sending notifications with shared logic.

    This class encapsulates the common pattern of:
    1. Checking user preferences
    2. Creating a notification record
    3. Sending the email
    4. Updating the notification status
    """

    # Map notification types to preference keys
    PREFERENCE_KEYS: dict[NotificationType, str] = {
        NotificationType.COURSE_UPDATE: "course_updates",
        NotificationType.ANNOUNCEMENT: "admin_announcements",
        NotificationType.DIRECT_MESSAGE: "direct_messages",
    }

    def __init__(self, db: Session):
        self.db = db
        self.email_service = get_email_service()

    def should_send(self, user: User, notification_type: NotificationType) -> bool:
        """Check if notification should be sent based on user preferences.

        Args:
            user: The user to check preferences for.
            notification_type: Type of notification to check.

        Returns:
            True if notification should be sent, False if user opted out.
        """
        prefs = user.notification_preferences or {}
        preference_key = self.PREFERENCE_KEYS.get(notification_type)

        if preference_key is None:
            return True

        result: bool = prefs.get(preference_key, True)
        return result

    def create_notification(self, ctx: NotificationContext) -> Notification:
        """Create a pending notification record.

        Args:
            ctx: Notification context with all required data.

        Returns:
            Created Notification instance (already added to session).
        """
        notification = Notification(
            user_id=ctx.user.id,
            notification_type=ctx.notification_type.value,
            subject=ctx.subject,
            status=NotificationStatus.PENDING.value,
            course_id=ctx.course_id,
            announcement_log_id=ctx.announcement_log_id,
        )
        self.db.add(notification)
        return notification

    def send_and_update(
        self, notification: Notification, email_message: EmailMessage
    ) -> SendResult:
        """Send email and update notification status.

        Args:
            notification: The notification record to update.
            email_message: The email to send.

        Returns:
            SendResult indicating success or failure.
        """
        try:
            success = asyncio.run(self.email_service.send_email(email_message))

            if success:
                notification.status = NotificationStatus.SENT.value
                notification.sent_at = datetime.now(UTC)
                self.db.commit()
                return SendResult(sent=True)
            else:
                notification.status = NotificationStatus.FAILED.value
                notification.error_message = "Email service returned False"
                self.db.commit()
                return SendResult(sent=False, failed=True, reason="email_service_false")

        except Exception as exc:
            notification.status = NotificationStatus.FAILED.value
            notification.error_message = str(exc)[:500]
            self.db.commit()
            logger.exception("Failed to send email to %s", email_message.to)
            return SendResult(sent=False, failed=True, reason=str(exc)[:200])

    def process_user_notification(
        self,
        user: User,
        notification_type: NotificationType,
        email_builder: Any,  # Callable that returns EmailMessage
        **extra_ctx: Any,
    ) -> SendResult:
        """Process a single user notification with the full workflow.

        This is a convenience method that combines:
        - Preference check
        - Notification creation
        - Email sending
        - Status update

        Args:
            user: Target user.
            notification_type: Type of notification.
            email_builder: Callable that returns an EmailMessage.
            **extra_ctx: Additional context for notification (course_id, announcement_log_id).

        Returns:
            SendResult indicating the outcome.
        """
        if not self.should_send(user, notification_type):
            return SendResult(sent=False, skipped=True, reason="opted_out")

        email_message = email_builder()

        ctx = NotificationContext(
            user=user,
            notification_type=notification_type,
            subject=email_message.subject,
            email_message=email_message,
            course_id=extra_ctx.get("course_id"),
            announcement_log_id=extra_ctx.get("announcement_log_id"),
        )

        notification = self.create_notification(ctx)
        return self.send_and_update(notification, email_message)
