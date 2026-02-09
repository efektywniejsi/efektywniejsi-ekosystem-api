import uuid
from datetime import datetime
from typing import cast

from sqlalchemy.orm import Session

from app.packages.models.order import Order, OrderItem, OrderStatus, PaymentProvider
from app.packages.models.package import Package
from app.packages.services.payment_service import PaymentServiceFactory
from app.packages.utils.order_number import generate_order_number


class CheckoutService:
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
        customer_ip: str = "127.0.0.1",
        wants_invoice: bool = False,
        buyer_tax_no: str | None = None,
        buyer_company_name: str | None = None,
        buyer_street: str | None = None,
        buyer_post_code: str | None = None,
        buyer_city: str | None = None,
    ) -> dict[str, str]:
        packages = self._validate_packages(package_ids)

        subtotal = sum(pkg.price for pkg in packages)
        total = subtotal

        order = Order(
            id=uuid.uuid4(),
            order_number=generate_order_number(),
            user_id=None,
            email=email,
            name=name,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            total=total,
            currency="PLN",
            payment_provider=payment_provider,
            webhook_processed=False,
            # Invoice billing info (optional)
            buyer_tax_no=buyer_tax_no if wants_invoice else None,
            buyer_company_name=buyer_company_name if wants_invoice else None,
            buyer_street=buyer_street if wants_invoice else None,
            buyer_post_code=buyer_post_code if wants_invoice else None,
            buyer_city=buyer_city if wants_invoice else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(order)
        self.db.flush()

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
        self.db.refresh(order)

        payment_service = PaymentServiceFactory.get_service(payment_provider)
        payment_result = await payment_service.create_payment_session(
            order, success_url, cancel_url, customer_ip=customer_ip
        )

        order.payment_intent_id = payment_result["session_id"]
        self.db.commit()

        return {
            "payment_url": payment_result["url"],
            "order_id": str(order.id),
        }

    def _validate_packages(self, package_ids: list[str]) -> list[Package]:
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
        try:
            order_uuid = uuid.UUID(order_id)
        except ValueError:
            return None

        return cast(Order | None, self.db.query(Order).filter(Order.id == order_uuid).first())
