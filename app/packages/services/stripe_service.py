"""
Stripe payment integration service.
"""

from typing import Any

import stripe

from app.core.config import settings
from app.packages.models.order import Order
from app.packages.services.payment_service import PaymentService

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService(PaymentService):
    """Stripe payment service implementation."""

    async def create_payment_session(
        self, order: Order, success_url: str, cancel_url: str
    ) -> dict[str, Any]:
        """
        Create a Stripe Checkout session.

        Creates a hosted payment page with all order items.
        """
        # Build line items from order items
        line_items = []
        for item in order.items:
            line_items.append(
                {
                    "price_data": {
                        "currency": order.currency.lower(),
                        "unit_amount": item.price,  # Price in grosz
                        "product_data": {
                            "name": item.package_title,
                            "description": f"Pakiet: {item.package_slug}",
                        },
                    },
                    "quantity": 1,
                }
            )

        # Create Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card", "blik"],
            line_items=line_items,
            mode="payment",
            success_url=f"{success_url}?order_id={order.id}",
            cancel_url=cancel_url,
            customer_email=order.email,
            metadata={
                "order_id": str(order.id),
                "order_number": order.order_number,
            },
            # Expires after 30 minutes
            expires_at=int(order.created_at.timestamp() + 1800),
        )

        return {
            "url": session.url,
            "session_id": session.id,
        }

    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """
        Verify Stripe webhook signature and parse event.

        Raises:
            ValueError: If signature verification fails
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f"Invalid signature: {e}") from e
        except Exception as e:
            raise ValueError(f"Webhook verification failed: {e}") from e
