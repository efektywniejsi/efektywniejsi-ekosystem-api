from typing import Any, cast

import stripe  # type: ignore[import-untyped]

from app.core.config import settings
from app.packages.models.order import Order
from app.packages.services.payment_service import PaymentService

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService(PaymentService):
    async def create_payment_session(
        self, order: Order, success_url: str, cancel_url: str, customer_ip: str = "127.0.0.1"
    ) -> dict[str, Any]:
        line_items = [
            {
                "price_data": {
                    "currency": order.currency.lower(),
                    "unit_amount": item.price,
                    "product_data": {
                        "name": item.package_title,
                        "description": f"Pakiet: {item.package_slug}",
                    },
                },
                "quantity": 1,
            }
            for item in order.items
        ]

        session = stripe.checkout.Session.create(
            payment_method_types=["card", "blik"],
            line_items=cast(Any, line_items),
            mode="payment",
            success_url=f"{success_url}?order_id={order.id}",
            cancel_url=cancel_url,
            customer_email=order.email,
            metadata={
                "order_id": str(order.id),
                "order_number": order.order_number,
            },
            expires_at=int(order.created_at.timestamp() + 1800),
        )

        return {
            "url": session.url,
            "session_id": session.id,
        }

    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return cast(dict[str, Any], event)
        except stripe.error.SignatureVerificationError as e:  # type: ignore[attr-defined]
            raise ValueError(f"Invalid signature: {e}") from e
        except Exception as e:
            raise ValueError(f"Webhook verification failed: {e}") from e
