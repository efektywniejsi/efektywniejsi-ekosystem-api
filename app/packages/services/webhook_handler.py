"""Abstract webhook handler for payment providers.

This module provides a common interface and shared logic for handling
payment webhooks from different providers (Stripe, PayU).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.packages.models.order import Order
from app.packages.services.email_service import (
    send_purchase_confirmation_email,
    send_welcome_with_package_email,
)
from app.packages.services.fakturownia_service import get_fakturownia_service
from app.packages.services.order_service import OrderService

logger = logging.getLogger(__name__)


@dataclass
class WebhookResult:
    """Result of webhook processing."""

    status: str
    order_id: str | None = None
    message: str | None = None


class WebhookHandler(ABC):
    """Abstract base class for payment webhook handlers."""

    def __init__(self, db: Session):
        self.db = db

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the payment provider."""
        ...

    @abstractmethod
    async def verify_signature(self, payload: bytes, signature: str) -> dict:
        """Verify the webhook signature and parse the payload.

        Args:
            payload: Raw request body bytes.
            signature: Signature header value.

        Returns:
            Parsed event data.

        Raises:
            ValueError: If signature verification fails.
        """
        ...

    @abstractmethod
    def extract_payment_info(self, event: dict) -> tuple[str | None, bool]:
        """Extract payment information from the event.

        Args:
            event: Parsed webhook event data.

        Returns:
            Tuple of (payment_intent_id, should_process).
            - payment_intent_id: The ID to look up the order, or None if not applicable.
            - should_process: Whether this event should trigger payment processing.
        """
        ...

    async def process(self, payload: bytes, signature: str) -> WebhookResult:
        """Process the webhook request.

        This is the main entry point that orchestrates signature verification,
        event parsing, and payment processing.

        Args:
            payload: Raw request body bytes.
            signature: Signature header value.

        Returns:
            WebhookResult with processing status.

        Raises:
            HTTPException: If signature verification fails.
        """
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brak sygnatury {self.provider_name}",
            )

        try:
            event = await self.verify_signature(payload, signature)
        except ValueError as e:
            logger.error(f"{self.provider_name} webhook verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Weryfikacja sygnatury nie powiodła się",
            ) from e

        payment_intent_id, should_process = self.extract_payment_info(event)

        if not should_process:
            event_type = event.get("type", "unknown")
            logger.info(f"Received {self.provider_name} event: {event_type}")
            return WebhookResult(status="acknowledged")

        if not payment_intent_id:
            logger.error(f"{self.provider_name} event missing payment_intent_id")
            return WebhookResult(status="error", message="Missing payment ID")

        logger.info(f"Processing {self.provider_name} payment: {payment_intent_id}")

        order = self.db.query(Order).filter(Order.payment_intent_id == payment_intent_id).first()

        if not order:
            logger.error(f"Order not found for payment_intent_id: {payment_intent_id}")
            return WebhookResult(status="error", message="Order not found")

        try:
            await self._process_payment(order)
            return WebhookResult(status="success", order_id=str(order.id))
        except Exception as e:
            logger.error(
                f"{self.provider_name} webhook processing error for order {order.id}: {e}",
                exc_info=True,
            )
            # Return 200 to prevent retries; generic message hides internal state
            return WebhookResult(status="error", message="Błąd przetwarzania płatności")

    async def _process_payment(self, order: Order) -> dict[str, str]:
        """Process a successful payment.

        Handles order completion, user creation/lookup, enrollment,
        and sending confirmation emails.
        """
        order_service = OrderService(self.db)
        result = await order_service.process_successful_payment(order)

        if result["status"] == "already_processed":
            logger.info(f"Order {order.id} already processed, skipping")
            return {"status": "already_processed"}

        user = result["user"]
        enrollments = result["enrollments"]
        is_new_user = result["is_new_user"]

        try:
            if is_new_user:
                reset_token = result["reset_token"]
                await send_welcome_with_package_email(
                    name=user.name,
                    email=user.email,
                    order=order,
                    enrollments=enrollments,
                    reset_token=reset_token,
                )
                logger.info(f"Sent welcome email to {user.email}")
            else:
                await send_purchase_confirmation_email(
                    name=user.name,
                    email=user.email,
                    order=order,
                    enrollments=enrollments,
                )
                logger.info(f"Sent purchase confirmation email to {user.email}")

        except Exception as e:
            # Log but don't fail -- the payment was already processed successfully
            logger.error(f"Failed to send email: {e}")

        # Generate invoice via Fakturownia (non-blocking)
        await self._generate_invoice(order)

        logger.info(
            f"Successfully processed order {order.order_number}: "
            f"{len(enrollments)} enrollments created"
        )

        return {"status": "success"}

    async def _generate_invoice(self, order: Order) -> None:
        """Generate invoice for the order via Fakturownia.

        This is a non-critical operation - failures are logged but don't
        affect the overall payment processing.
        """
        try:
            fakturownia = get_fakturownia_service()

            if not fakturownia.is_configured:
                logger.debug("Fakturownia not configured, skipping invoice generation")
                return

            result = await fakturownia.create_invoice(order)

            if result.success:
                # Update order with invoice data
                from datetime import UTC, datetime

                order.fakturownia_invoice_id = result.invoice_id
                order.invoice_number = result.invoice_number
                order.invoice_token = result.invoice_token
                order.invoice_issued_at = datetime.now(UTC)
                self.db.commit()

                logger.info(
                    f"Invoice {result.invoice_number} created for order {order.order_number}"
                )
            else:
                logger.warning(
                    f"Failed to create invoice for order {order.order_number}: {result.error}"
                )

        except Exception as e:
            # Never fail payment processing due to invoice generation errors
            logger.error(
                f"Invoice generation error for order {order.order_number}: {e}",
                exc_info=True,
            )
