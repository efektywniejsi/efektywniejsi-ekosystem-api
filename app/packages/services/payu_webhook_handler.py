"""PayU webhook handler implementation."""

from sqlalchemy.orm import Session

from app.packages.models.order import PaymentProvider
from app.packages.services.payment_service import PaymentServiceFactory
from app.packages.services.webhook_handler import WebhookHandler


class PayUWebhookHandler(WebhookHandler):
    """Webhook handler for PayU payments."""

    @property
    def provider_name(self) -> str:
        return "PayU"

    async def verify_signature(self, payload: bytes, signature: str) -> dict:
        """Verify PayU webhook signature and parse payload."""
        payu_service = PaymentServiceFactory.get_service(PaymentProvider.PAYU)
        event: dict = await payu_service.verify_webhook(payload, signature)
        return event

    def extract_payment_info(self, event: dict) -> tuple[str | None, bool]:
        """Extract payment information from PayU event.

        Returns:
            Tuple of (payment_intent_id, should_process).
        """
        if "order" in event:
            order_data = event["order"]
            payment_intent_id = order_data.get("orderId")
            payu_status = order_data.get("status")

            # Only process COMPLETED payments
            if payu_status == "COMPLETED":
                return payment_intent_id, True

            return payment_intent_id, False

        return None, False


def get_payu_handler(db: Session) -> PayUWebhookHandler:
    """Factory function for PayU webhook handler."""
    return PayUWebhookHandler(db)
