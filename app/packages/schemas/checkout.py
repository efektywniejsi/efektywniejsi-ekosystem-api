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


class CheckoutInitiateResponse(BaseModel):
    """Response from checkout initiation."""

    payment_url: str = Field(..., description="URL to redirect user for payment")
    order_id: uuid.UUID = Field(..., description="Created order ID")


class OrderStatusResponse(BaseModel):
    """Response for order status check."""

    order_id: uuid.UUID
    order_number: str
    status: str
    total: int  # In grosz
    currency: str
    webhook_processed: bool
