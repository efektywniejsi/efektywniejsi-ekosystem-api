import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYU = "payu"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    order_number: Mapped[str] = mapped_column(unique=True, index=True)  # ORD-20260121-XXXX

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, default=None
    )  # NULL before account creation
    email: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column()

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=OrderStatus.PENDING,
        index=True,
    )
    subtotal: Mapped[int] = mapped_column()  # In grosz
    total: Mapped[int] = mapped_column()  # In grosz
    currency: Mapped[str] = mapped_column(default="PLN")

    payment_provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, values_callable=lambda obj: [e.value for e in obj])
    )
    payment_intent_id: Mapped[str | None] = mapped_column(
        default=None, index=True
    )  # Payment session ID
    payment_completed_at: Mapped[datetime | None] = mapped_column(default=None)

    webhook_processed: Mapped[bool] = mapped_column(default=False, index=True)  # Idempotency flag

    # Invoice (Fakturownia integration)
    fakturownia_invoice_id: Mapped[int | None] = mapped_column(default=None, index=True)
    invoice_number: Mapped[str | None] = mapped_column(default=None)  # e.g., "FV/2026/02/001"
    invoice_token: Mapped[str | None] = mapped_column(default=None)  # Public access token for PDF
    invoice_issued_at: Mapped[datetime | None] = mapped_column(default=None)

    # Optional buyer tax info (for B2B invoices)
    buyer_tax_no: Mapped[str | None] = mapped_column(default=None)  # NIP
    buyer_company_name: Mapped[str | None] = mapped_column(default=None)
    buyer_street: Mapped[str | None] = mapped_column(default=None)
    buyer_post_code: Mapped[str | None] = mapped_column(default=None)
    buyer_city: Mapped[str | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    user = relationship("User", backref="orders")

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, order_number={self.order_number}, status={self.status.value})>"
        )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )

    # Snapshot at purchase time
    package_title: Mapped[str] = mapped_column()
    package_slug: Mapped[str] = mapped_column()
    price: Mapped[int] = mapped_column()  # In grosz

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Relationships
    order = relationship("Order", back_populates="items")
    package = relationship("Package")

    def __repr__(self) -> str:
        return (
            f"<OrderItem(id={self.id}, order_id={self.order_id}, "
            f"package_title={self.package_title})>"
        )
