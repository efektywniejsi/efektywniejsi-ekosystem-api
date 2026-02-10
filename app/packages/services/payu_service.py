import hashlib
import json
from typing import Any, cast

import httpx  # type: ignore[import-not-found]

from app.core.config import settings
from app.packages.models.order import Order
from app.packages.services.payment_service import PaymentService


class PayUService(PaymentService):
    def __init__(self) -> None:
        self.api_url = settings.PAYU_API_URL
        self.merchant_id = settings.PAYU_MERCHANT_ID
        self.secret_key = settings.PAYU_SECRET_KEY
        self.webhook_secret = settings.PAYU_WEBHOOK_SECRET

    async def _get_oauth_token(self) -> str:
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
            return cast(str, data["access_token"])

    async def create_payment_session(
        self, order: Order, success_url: str, cancel_url: str, customer_ip: str = "127.0.0.1"
    ) -> dict[str, Any]:
        access_token = await self._get_oauth_token()

        products = [
            {
                "name": item.package_title,
                "unitPrice": item.price,
                "quantity": 1,
            }
            for item in order.items
        ]

        order_data = {
            "notifyUrl": f"{settings.BACKEND_URL}/api/v1/webhooks/payu",
            "customerIp": customer_ip,
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
        if not self.webhook_secret:
            raise ValueError("PAYU_WEBHOOK_SECRET not configured")

        # PayU sends signature header in format:
        # sender=checkout;signature=<sig>;algorithm=MD5|SHA-256;content=DOCUMENT
        signature_value = None
        algorithm = "MD5"  # Default to MD5 for backwards compatibility
        for part in signature.split(";"):
            key_value = part.split("=", 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                if key == "signature":
                    signature_value = value
                elif key == "algorithm":
                    algorithm = value.upper()

        if not signature_value:
            raise ValueError("Could not parse signature from OpenPayu-Signature header")

        # PayU notification signature: hash(json_body + secondKey)
        # Use the algorithm specified in the header
        if algorithm == "SHA-256" or algorithm == "SHA256":
            expected_signature = hashlib.sha256(payload + self.webhook_secret.encode()).hexdigest()
        elif algorithm == "SHA-384" or algorithm == "SHA384":
            expected_signature = hashlib.sha384(payload + self.webhook_secret.encode()).hexdigest()
        elif algorithm == "SHA-512" or algorithm == "SHA512":
            expected_signature = hashlib.sha512(payload + self.webhook_secret.encode()).hexdigest()
        else:
            # MD5 (legacy, but still used by PayU in some configurations)
            expected_signature = hashlib.md5(payload + self.webhook_secret.encode()).hexdigest()

        if signature_value != expected_signature:
            raise ValueError("Invalid webhook signature")

        try:
            event_data = json.loads(payload.decode("utf-8"))
            return cast(dict[str, Any], event_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e
