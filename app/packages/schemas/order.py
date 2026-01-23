"""
Pydantic schemas for orders.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

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
    payment_completed_at: datetime | None
    created_at: datetime
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
    created_at: datetime
    items_count: int

    class Config:
        from_attributes = True
