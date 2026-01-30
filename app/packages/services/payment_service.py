from abc import ABC, abstractmethod
from typing import Any

from app.packages.models.order import Order, PaymentProvider


class PaymentService(ABC):
    @abstractmethod
    async def create_payment_session(
        self, order: Order, success_url: str, cancel_url: str, customer_ip: str = "127.0.0.1"
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        pass


class PaymentServiceFactory:
    @staticmethod
    def get_service(provider: PaymentProvider) -> PaymentService:
        if provider == PaymentProvider.STRIPE:
            from app.packages.services.stripe_service import StripeService

            return StripeService()
        elif provider == PaymentProvider.PAYU:
            from app.packages.services.payu_service import PayUService

            return PayUService()
        else:
            raise ValueError(f"Unsupported payment provider: {provider}")
