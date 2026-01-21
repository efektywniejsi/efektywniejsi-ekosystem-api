"""
Checkout service for order creation and payment initiation.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.packages.models.order import Order, OrderItem, OrderStatus, PaymentProvider
from app.packages.models.package import Package
from app.packages.services.payment_service import PaymentServiceFactory
from app.packages.utils.order_number import generate_order_number


class CheckoutService:
    """Service for handling checkout and order creation."""

    def __init__(self, db: Session):
        self.db = db

    async def initiate_checkout(
        self,
        package_ids: list[str],
        email: str,
        name: str,
        payment_provider: PaymentProvider,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, str]:
        """
        Initiate checkout process.

        Steps:
        1. Validate all packages exist
        2. Create Order with PENDING status
        3. Create OrderItems
        4. Initiate payment with selected provider
        5. Return payment URL

        Args:
            package_ids: List of package UUIDs to purchase
            email: Customer email
            name: Customer name
            payment_provider: Selected payment provider (stripe/payu)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled

        Returns:
            Dictionary with payment_url and order_id

        Raises:
            ValueError: If packages not found or validation fails
        """
        # 1. Validate packages
        packages = self._validate_packages(package_ids)

        # 2. Calculate totals
        subtotal = sum(pkg.price for pkg in packages)
        total = subtotal  # Can add taxes/fees here

        # 3. Create order
        order = Order(
            id=uuid.uuid4(),
            order_number=generate_order_number(),
            user_id=None,  # Will be set after payment
            email=email,
            name=name,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            total=total,
            currency="PLN",
            payment_provider=payment_provider,
            webhook_processed=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(order)
        self.db.flush()  # Get order.id

        # 4. Create order items
        for package in packages:
            order_item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                package_id=package.id,
                package_title=package.title,
                package_slug=package.slug,
                price=package.price,
                created_at=datetime.utcnow(),
            )
            self.db.add(order_item)

        self.db.commit()

        # 5. Refresh order to load items relationship
        self.db.refresh(order)

        # 6. Initiate payment
        payment_service = PaymentServiceFactory.get_service(payment_provider)
        payment_result = await payment_service.create_payment_session(
            order, success_url, cancel_url
        )

        # 7. Update order with payment intent ID
        order.payment_intent_id = payment_result["session_id"]
        self.db.commit()

        return {
            "payment_url": payment_result["url"],
            "order_id": str(order.id),
        }

    def _validate_packages(self, package_ids: list[str]) -> list[Package]:
        """
        Validate that all packages exist and are published.

        Raises:
            ValueError: If any package is not found or not published
        """
        if not package_ids:
            raise ValueError("No packages provided")

        packages = []
        for pkg_id in package_ids:
            try:
                package_uuid = uuid.UUID(pkg_id)
            except ValueError as e:
                raise ValueError(f"Invalid package ID format: {pkg_id}") from e

            package = (
                self.db.query(Package)
                .filter(Package.id == package_uuid, Package.is_published == True)  # noqa: E712
                .first()
            )

            if not package:
                raise ValueError(f"Package not found or not available: {pkg_id}")

            packages.append(package)

        return packages

    def get_order_by_id(self, order_id: str) -> Order | None:
        """Get order by ID."""
        try:
            order_uuid = uuid.UUID(order_id)
        except ValueError:
            return None

        return self.db.query(Order).filter(Order.id == order_uuid).first()  # type: ignore[no-any-return]
