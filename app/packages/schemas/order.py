"""
Pydantic schemas for orders.

Note: Invoice information (invoice_number, invoice_issued_at) is stored internally
but not exposed to users. Invoices are sent via Fakturownia email automatically.
"""

import uuid

from pydantic import BaseModel

from app.core.datetime_utils import UTCDatetime
from app.packages.models.order import OrderStatus, PaymentProvider


class OrderItemResponse(BaseModel):
    """Order item response schema."""

    id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    package_slug: str
    price: int  # In grosz

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response schema."""

    id: uuid.UUID
    order_number: str
    email: str
    name: str
    status: OrderStatus
    subtotal: int  # In grosz
    total: int  # In grosz
    currency: str
    payment_provider: PaymentProvider
    payment_completed_at: UTCDatetime | None
    created_at: UTCDatetime
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Order list response (for user's order history)."""

    id: uuid.UUID
    order_number: str
    status: OrderStatus
    total: int  # In grosz
    currency: str
    created_at: UTCDatetime
    items_count: int

    class Config:
        from_attributes = True
