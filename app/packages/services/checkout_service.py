import uuid
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.implementation_packages.models.implementation_package import (
    ImplementationPackage,
    ImplementationPackageEnrollment,
)
from app.packages.models.enrollment import PackageEnrollment
from app.packages.models.order import Order, OrderItem, OrderStatus, PaymentProvider
from app.packages.models.package import Package
from app.packages.services.payment_service import PaymentServiceFactory
from app.packages.utils.order_number import generate_order_number


class CheckoutService:
    def __init__(self, db: Session):
        self.db = db

    async def initiate_checkout(
        self,
        package_ids: list[str] | None,
        email: str,
        name: str,
        payment_provider: PaymentProvider,
        success_url: str,
        cancel_url: str,
        customer_ip: str = "127.0.0.1",
        user_id: uuid.UUID | None = None,
        wants_invoice: bool = False,
        buyer_tax_no: str | None = None,
        buyer_company_name: str | None = None,
        buyer_street: str | None = None,
        buyer_post_code: str | None = None,
        buyer_city: str | None = None,
        implementation_package_ids: list[str] | None = None,
    ) -> dict[str, str]:
        packages: list[Package] = []
        impl_packages: list[ImplementationPackage] = []

        if package_ids:
            packages = self._validate_packages(package_ids)
            if user_id:
                self._check_existing_enrollments(user_id, packages)
            else:
                self._check_existing_enrollments_by_email(email, packages)

        if implementation_package_ids:
            impl_packages = self._validate_implementation_packages(implementation_package_ids)
            if user_id:
                self._check_existing_impl_enrollments(user_id, impl_packages)
            else:
                self._check_existing_impl_enrollments_by_email(email, impl_packages)

        if not packages and not impl_packages:
            raise ValueError("Musisz wybrać co najmniej jeden produkt do zakupu")

        subtotal = sum(pkg.price for pkg in packages) + sum(pkg.price for pkg in impl_packages)
        total = subtotal

        order = Order(
            id=uuid.uuid4(),
            order_number=generate_order_number(),
            user_id=user_id,
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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
                created_at=datetime.now(UTC),
            )
            self.db.add(order_item)

        for impl_pkg in impl_packages:
            order_item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                implementation_package_id=impl_pkg.id,
                package_title=impl_pkg.title,
                package_slug=impl_pkg.slug,
                price=impl_pkg.price,
                created_at=datetime.now(UTC),
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

    def _check_existing_enrollments(self, user_id: uuid.UUID, packages: list[Package]) -> None:
        package_ids = [pkg.id for pkg in packages]
        enrolled_ids = {
            row[0]
            for row in self.db.query(PackageEnrollment.package_id)
            .filter(
                PackageEnrollment.user_id == user_id,
                PackageEnrollment.package_id.in_(package_ids),
            )
            .all()
        }
        for pkg in packages:
            if pkg.id in enrolled_ids:
                raise ValueError(f"Masz już dostęp do pakietu: {pkg.title}")

    def _check_existing_enrollments_by_email(self, email: str, packages: list[Package]) -> None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return

        package_ids = [pkg.id for pkg in packages]
        enrolled_ids = {
            row[0]
            for row in self.db.query(PackageEnrollment.package_id)
            .filter(
                PackageEnrollment.user_id == user.id,
                PackageEnrollment.package_id.in_(package_ids),
            )
            .all()
        }
        for pkg in packages:
            if pkg.id in enrolled_ids:
                raise ValueError(
                    f"Masz już dostęp do pakietu: {pkg.title}. "
                    "Zaloguj się do dashboardu, aby uzyskać dostęp."
                )

    def _check_existing_impl_enrollments(
        self, user_id: uuid.UUID, packages: list[ImplementationPackage]
    ) -> None:
        package_ids = [pkg.id for pkg in packages]
        enrolled_ids = {
            row[0]
            for row in self.db.query(ImplementationPackageEnrollment.package_id)
            .filter(
                ImplementationPackageEnrollment.user_id == user_id,
                ImplementationPackageEnrollment.package_id.in_(package_ids),
            )
            .all()
        }
        for pkg in packages:
            if pkg.id in enrolled_ids:
                raise ValueError(f"Masz już dostęp do pakietu: {pkg.title}")

    def _check_existing_impl_enrollments_by_email(
        self, email: str, packages: list[ImplementationPackage]
    ) -> None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return

        package_ids = [pkg.id for pkg in packages]
        enrolled_ids = {
            row[0]
            for row in self.db.query(ImplementationPackageEnrollment.package_id)
            .filter(
                ImplementationPackageEnrollment.user_id == user.id,
                ImplementationPackageEnrollment.package_id.in_(package_ids),
            )
            .all()
        }
        for pkg in packages:
            if pkg.id in enrolled_ids:
                raise ValueError(
                    f"Masz już dostęp do pakietu: {pkg.title}. "
                    "Zaloguj się do dashboardu, aby uzyskać dostęp."
                )

    def _validate_packages(self, package_ids: list[str]) -> list[Package]:
        if not package_ids:
            return []

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

    def _validate_implementation_packages(
        self, package_ids: list[str]
    ) -> list[ImplementationPackage]:
        if not package_ids:
            return []

        packages = []
        for pkg_id in package_ids:
            try:
                package_uuid = uuid.UUID(pkg_id)
            except ValueError as e:
                raise ValueError(f"Invalid package ID format: {pkg_id}") from e

            package = (
                self.db.query(ImplementationPackage)
                .filter(
                    ImplementationPackage.id == package_uuid,
                    ImplementationPackage.is_published == True,  # noqa: E712
                )
                .first()
            )

            if not package:
                raise ValueError(f"Pakiet wdrożeniowy nie został znaleziony: {pkg_id}")

            packages.append(package)

        return packages

    def get_order_by_id(self, order_id: str) -> Order | None:
        try:
            order_uuid = uuid.UUID(order_id)
        except ValueError:
            return None

        return cast(Order | None, self.db.query(Order).filter(Order.id == order_uuid).first())
