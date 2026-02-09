"""Fakturownia.pl invoice generation service.

This module integrates with Fakturownia.pl API to generate VAT invoices
for completed orders.

API Documentation: https://github.com/fakturownia/API
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx  # type: ignore[import-not-found]

from app.core.config import settings
from app.packages.models.order import Order

logger = logging.getLogger(__name__)


@dataclass
class InvoiceResult:
    """Result of invoice creation."""

    success: bool
    invoice_id: int | None = None
    invoice_number: str | None = None
    invoice_token: str | None = None  # Public access token for PDF
    error: str | None = None


class FakturowniaService:
    """Service for generating invoices via Fakturownia.pl API."""

    def __init__(self) -> None:
        self.api_token = settings.FAKTUROWNIA_API_TOKEN
        self.subdomain = settings.FAKTUROWNIA_SUBDOMAIN
        self.base_url = f"https://{self.subdomain}.fakturownia.pl"

    @property
    def is_configured(self) -> bool:
        """Check if Fakturownia is properly configured."""
        return bool(self.api_token and self.subdomain)

    def get_invoice_pdf_url(self, invoice_token: str) -> str:
        """Get public PDF URL for an invoice."""
        return f"{self.base_url}/invoice/{invoice_token}.pdf"

    async def create_invoice(self, order: Order) -> InvoiceResult:
        """Create a VAT invoice for a completed order.

        Args:
            order: The completed order to create an invoice for.

        Returns:
            InvoiceResult with invoice details or error.
        """
        if not self.is_configured:
            logger.warning("Fakturownia not configured, skipping invoice generation")
            return InvoiceResult(
                success=False,
                error="Fakturownia not configured",
            )

        try:
            invoice_data = self._build_invoice_data(order)
            result = await self._send_invoice_request(invoice_data)
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "Fakturownia API error for order %s: %s - %s",
                order.order_number,
                e.response.status_code,
                e.response.text,
            )
            return InvoiceResult(
                success=False,
                error=f"API error: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            logger.error(
                "Fakturownia connection error for order %s: %s",
                order.order_number,
                str(e),
            )
            return InvoiceResult(
                success=False,
                error=f"Connection error: {str(e)}",
            )
        except Exception as e:
            logger.error(
                "Unexpected error creating invoice for order %s: %s",
                order.order_number,
                str(e),
                exc_info=True,
            )
            return InvoiceResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    def _build_invoice_data(self, order: Order) -> dict[str, Any]:
        """Build the invoice request payload."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # Payment type based on provider
        payment_type = "card" if order.payment_provider.value == "stripe" else "transfer"

        # Build positions from order items
        positions = []
        for item in order.items:
            # Prices in Order are stored in grosz (1/100 PLN)
            # Fakturownia expects decimal values
            price_gross = item.price / 100.0

            positions.append(
                {
                    "name": item.package_title,
                    "quantity": 1,
                    "quantity_unit": "szt.",
                    "total_price_gross": price_gross,
                    "tax": 23,  # Standard Polish VAT rate
                }
            )

        # Determine buyer name - use company name if provided, otherwise personal name
        buyer_name = order.buyer_company_name or order.name

        invoice_payload: dict[str, Any] = {
            "api_token": self.api_token,
            "invoice": {
                "kind": "vat",
                "number": None,  # Auto-generate
                "sell_date": today,
                "issue_date": today,
                "payment_to": today,  # Already paid
                "payment_type": payment_type,
                "status": "paid",  # Mark as paid since payment is already completed
                "paid": str(order.total / 100.0),  # Amount paid
                "currency": order.currency,
                "lang": "pl",
                # Seller info from settings
                "seller_name": settings.FAKTUROWNIA_SELLER_NAME,
                "seller_tax_no": settings.FAKTUROWNIA_SELLER_TAX_NO,
                "seller_street": settings.FAKTUROWNIA_SELLER_STREET,
                "seller_post_code": settings.FAKTUROWNIA_SELLER_POST_CODE,
                "seller_city": settings.FAKTUROWNIA_SELLER_CITY,
                "seller_country": settings.FAKTUROWNIA_SELLER_COUNTRY,
                "seller_bank": settings.FAKTUROWNIA_SELLER_BANK,
                "seller_bank_account": settings.FAKTUROWNIA_SELLER_BANK_ACCOUNT,
                # Buyer info
                "buyer_name": buyer_name,
                "buyer_email": order.email,
                "buyer_tax_no": order.buyer_tax_no or "",
                "buyer_street": order.buyer_street or "",
                "buyer_post_code": order.buyer_post_code or "",
                "buyer_city": order.buyer_city or "",
                "buyer_country": "PL",
                # Positions
                "positions": positions,
                # Additional fields
                "description": f"Zamówienie nr {order.order_number}",
                "oid": str(order.id),  # External order ID for reference
                # Always send invoice via Fakturownia email
                "send_email": True,
            },
        }

        return invoice_payload

    async def _send_invoice_request(self, invoice_data: dict[str, Any]) -> InvoiceResult:
        """Send the invoice creation request to Fakturownia API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/invoices.json",
                json=invoice_data,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

            data = response.json()

            logger.info(
                "Invoice created successfully: %s (ID: %s)",
                data.get("number"),
                data.get("id"),
            )

            return InvoiceResult(
                success=True,
                invoice_id=data.get("id"),
                invoice_number=data.get("number"),
                invoice_token=data.get("token"),
            )


# Singleton instance
_fakturownia_service: FakturowniaService | None = None


def get_fakturownia_service() -> FakturowniaService:
    """Get or create Fakturownia service instance."""
    global _fakturownia_service
    if _fakturownia_service is None:
        _fakturownia_service = FakturowniaService()
    return _fakturownia_service
