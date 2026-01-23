"""
Abstract payment service interface and factory.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.packages.models.order import Order, PaymentProvider


class PaymentService(ABC):
    """Abstract base class for payment providers."""

    @abstractmethod
    async def create_payment_session(
        self, order: Order, success_url: str, cancel_url: str
    ) -> dict[str, Any]:
        """
        Create a payment session with the provider.

        Args:
            order: Order object with items
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled

        Returns:
            Dictionary with 'url' (payment page URL) and 'session_id' (payment intent ID)
        """
        pass

    @abstractmethod
    async def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """
        Verify and parse webhook event from payment provider.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature header

        Returns:
            Parsed event data

        Raises:
            ValueError: If signature verification fails
        """
        pass


class PaymentServiceFactory:
    """Factory for creating payment service instances."""

    @staticmethod
    def get_service(provider: PaymentProvider) -> PaymentService:
        """Get payment service instance for the specified provider."""
        if provider == PaymentProvider.STRIPE:
            from app.packages.services.stripe_service import StripeService

            return StripeService()
        elif provider == PaymentProvider.PAYU:
            from app.packages.services.payu_service import PayUService

            return PayUService()
        else:
            raise ValueError(f"Unsupported payment provider: {provider}")
