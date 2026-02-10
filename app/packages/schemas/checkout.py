"""
Pydantic schemas for checkout.
"""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.packages.models.order import PaymentProvider


class CheckoutInitiateRequest(BaseModel):
    """Request to initiate checkout."""

    package_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of package UUIDs to purchase",
    )
    email: EmailStr = Field(..., description="Customer email")
    name: str = Field(..., min_length=2, max_length=100, description="Customer name")
    payment_provider: PaymentProvider = Field(..., description="Selected payment provider")

    # Optional invoice/billing information (for B2B)
    wants_invoice: bool = Field(default=False, description="Whether customer wants a VAT invoice")
    buyer_tax_no: str | None = Field(
        default=None,
        max_length=20,
        description="Buyer NIP/VAT number (required if wants_invoice=True for companies)",
    )
    buyer_company_name: str | None = Field(
        default=None,
        max_length=200,
        description="Company name for invoice",
    )
    buyer_street: str | None = Field(default=None, max_length=200)
    buyer_post_code: str | None = Field(default=None, max_length=20)
    buyer_city: str | None = Field(default=None, max_length=100)


class CheckoutInitiateResponse(BaseModel):
    """Response from checkout initiation."""

    payment_url: str = Field(..., description="URL to redirect user for payment")
    order_id: uuid.UUID = Field(..., description="Created order ID")


class OrderStatusResponse(BaseModel):
    """Response for order status check.

    Note: Invoice is sent automatically via Fakturownia email,
    not accessible from our platform.
    """

    order_id: uuid.UUID
    order_number: str
    status: str
    total: int  # In grosz
    currency: str
    webhook_processed: bool
