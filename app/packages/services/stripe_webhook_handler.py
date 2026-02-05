"""Stripe webhook handler implementation."""

from sqlalchemy.orm import Session

from app.packages.models.order import PaymentProvider
from app.packages.services.payment_service import PaymentServiceFactory
from app.packages.services.webhook_handler import WebhookHandler


class StripeWebhookHandler(WebhookHandler):
    """Webhook handler for Stripe payments."""

    @property
    def provider_name(self) -> str:
        return "Stripe"

    async def verify_signature(self, payload: bytes, signature: str) -> dict:
        """Verify Stripe webhook signature and parse payload."""
        stripe_service = PaymentServiceFactory.get_service(PaymentProvider.STRIPE)
        event: dict = await stripe_service.verify_webhook(payload, signature)
        return event

    def extract_payment_info(self, event: dict) -> tuple[str | None, bool]:
        """Extract payment information from Stripe event.

        Returns:
            Tuple of (payment_intent_id, should_process).
        """
        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            payment_intent_id: str = session["id"]
            return payment_intent_id, True

        return None, False


def get_stripe_handler(db: Session) -> StripeWebhookHandler:
    """Factory function for Stripe webhook handler."""
    return StripeWebhookHandler(db)
