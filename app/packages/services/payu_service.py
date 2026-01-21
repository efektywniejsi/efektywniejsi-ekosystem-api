"""
PayU payment integration service.
"""

import hashlib
import hmac
from typing import Any

import httpx

from app.core.config import settings
from app.packages.models.order import Order
from app.packages.services.payment_service import PaymentService


class PayUService(PaymentService):
    """PayU payment service implementation."""

    def __init__(self) -> None:
        self.api_url = settings.PAYU_API_URL
        self.merchant_id = settings.PAYU_MERCHANT_ID
        self.secret_key = settings.PAYU_SECRET_KEY
        self.webhook_secret = settings.PAYU_WEBHOOK_SECRET

    async def _get_oauth_token(self) -> str:
        """Get OAuth 2.0 token from PayU."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/pl/standard/user/oauth/authorize",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.merchant_id,
                    "client_secret": self.secret_key,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            return data["access_token"]

    async def create_payment_session(
        self, order: Order, success_url: str, cancel_url: str
    ) -> dict[str, Any]:
        """
        Create a PayU order.

        Creates a payment order and returns the redirect URL.
        """
        # Get OAuth token
        access_token = await self._get_oauth_token()

        # Build products from order items
        products = []
        for item in order.items:
            products.append(
                {
                    "name": item.package_title,
                    "unitPrice": item.price,  # Price in grosz
                    "quantity": 1,
                }
            )

        # Create PayU order
        order_data = {
            "notifyUrl": f"{settings.FRONTEND_URL}/api/v1/webhooks/payu",
            "customerIp": "127.0.0.1",  # Should be passed from request
            "merchantPosId": self.merchant_id,
            "description": f"Zamówienie {order.order_number}",
            "currencyCode": order.currency,
            "totalAmount": order.total,
            "buyer": {
                "email": order.email,
                "firstName": order.name.split()[0] if order.name else "Customer",
                "lastName": " ".join(order.name.split()[1:]) if len(order.name.split()) > 1 else "",
            },
            "products": products,
            "extOrderId": str(order.id),
            "continueUrl": success_url,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/api/v2_1/orders",
                json=order_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
            )
            response.raise_for_status()
            data = response.json()

            return {
                "url": data["redirectUri"],
                "session_id": data["orderId"],
            }

    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """
        Verify PayU webhook signature (HMAC SHA-256).

        Raises:
            ValueError: If signature verification fails
        """
        if not self.webhook_secret:
            raise ValueError("PAYU_WEBHOOK_SECRET not configured")

        # Calculate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Verify signature
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid webhook signature")

        # Parse JSON payload
        import json

        try:
            event_data = json.loads(payload.decode("utf-8"))
            return event_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e
