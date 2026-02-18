"""
Order service for user creation and enrollment management.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core.security import generate_reset_token
from app.courses.models.enrollment import Enrollment
from app.implementation_packages.models.implementation_package import (
    ImplementationPackageEnrollment,
)
from app.packages.models.bundle import BundleCourseItem, BundleImplementationPackageItem
from app.packages.models.enrollment import PackageEnrollment
from app.packages.models.order import Order, OrderStatus
from app.packages.models.package import Package


class OrderService:
    """Service for managing orders, users, and enrollments."""

    def __init__(self, db: Session):
        self.db = db

    async def process_successful_payment(self, order: Order) -> dict[str, Any]:
        """
        Process a successful payment webhook.

        This is the core business logic for converting a paid order into user enrollments.

        Steps:
        1. Check idempotency (webhook_processed flag)
        2. Create or find user
        3. Create package enrollments (handling bundles)
        4. Update order status
        5. Return data for email sending

        Returns:
            Dictionary with user, order, and enrollment data
        """
        # 1. Idempotency check
        if order.webhook_processed:
            return {
                "status": "already_processed",
                "user": None,
                "order": order,
                "enrollments": [],
            }

        try:
            # 2. Create or find user
            user = self._get_or_create_user(order)
            is_new_user = user.hashed_password == "!"

            # 3. Create enrollments
            enrollments = await self._create_enrollments(order, user)

            # 4. Update order
            order.user_id = user.id
            order.status = OrderStatus.COMPLETED
            order.payment_completed_at = datetime.now(UTC)
            order.webhook_processed = True

            self.db.commit()

            return {
                "status": "success",
                "user": user,
                "order": order,
                "enrollments": enrollments,
                "is_new_user": is_new_user,
                "reset_token": getattr(user, "_raw_reset_token", None) if is_new_user else None,
            }

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to process payment: {e}") from e

    def _get_or_create_user(self, order: Order) -> User:
        """Get existing user or create a new one."""
        # Check if user exists
        existing_user = cast(
            User | None, self.db.query(User).filter(User.email == order.email).first()
        )

        if existing_user:
            # If user never set their password, generate a new reset token
            # so they can set it via the welcome email
            if existing_user.hashed_password == "!":
                raw_token, hashed_token, expiry = generate_reset_token()
                existing_user.password_reset_token = hashed_token
                existing_user.password_reset_token_expires = expiry
                # Store raw token for email - transient, not persisted
                existing_user._raw_reset_token = raw_token  # type: ignore[attr-defined]
            self._sync_invoice_data(existing_user, order)
            return existing_user

        # Create new user with unusable password
        raw_token, hashed_token, expiry = generate_reset_token()

        user = User(
            id=uuid.uuid4(),
            email=order.email,
            name=order.name,
            hashed_password="!",  # Unusable hash - forces password reset
            role="paid",
            is_active=True,
            password_reset_token=hashed_token,
            password_reset_token_expires=expiry,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        self._sync_invoice_data(user, order)
        self.db.add(user)
        self.db.flush()  # Get user.id

        # Store raw token as a transient attribute for email sending
        # Do NOT overwrite the hashed token on the model to avoid persisting it
        user._raw_reset_token = raw_token  # type: ignore[attr-defined]

        return user

    @staticmethod
    def _sync_invoice_data(user: User, order: Order) -> None:
        """Copy invoice data from order to user profile if provided."""
        if not order.buyer_tax_no:
            return
        user.buyer_tax_no = order.buyer_tax_no
        user.buyer_company_name = order.buyer_company_name
        user.buyer_street = order.buyer_street
        user.buyer_post_code = order.buyer_post_code
        user.buyer_city = order.buyer_city

    async def _create_enrollments(
        self, order: Order, user: User
    ) -> list[PackageEnrollment | ImplementationPackageEnrollment]:
        """
        Create package enrollments from order items.

        Handles bundle packages by enrolling in:
        - Child packages (via PackageBundleItem)
        - Courses (via BundleCourseItem)
        """
        enrollments = []

        for order_item in order.items:
            # Handle ImplementationPackage items
            if order_item.implementation_package_id:
                impl_enrollment = self._create_impl_package_enrollment(
                    user.id, order_item.implementation_package_id, order.id
                )
                if impl_enrollment:
                    enrollments.append(impl_enrollment)
                continue

            package = self.db.query(Package).filter(Package.id == order_item.package_id).first()

            if not package:
                continue

            if package.is_bundle:
                # 1. Enroll in all child packages
                for bundle_item in package.bundle_items:
                    enrollment = self._create_single_enrollment(
                        user.id, bundle_item.child_package_id, order.id
                    )
                    if enrollment:
                        enrollments.append(enrollment)

                # 2. Enroll in all courses (NEW!)
                course_items = (
                    self.db.query(BundleCourseItem)
                    .filter(BundleCourseItem.bundle_id == package.id)
                    .all()
                )

                for course_item in course_items:
                    # Check if already enrolled
                    existing = (
                        self.db.query(Enrollment)
                        .filter(
                            Enrollment.user_id == user.id,
                            Enrollment.course_id == course_item.course_id,
                        )
                        .first()
                    )

                    if not existing:
                        expires_at = None
                        if course_item.access_duration_days is not None:
                            expires_at = datetime.now(UTC) + timedelta(
                                days=course_item.access_duration_days
                            )

                        course_enrollment = Enrollment(
                            user_id=user.id,
                            course_id=course_item.course_id,
                            expires_at=expires_at,
                        )
                        self.db.add(course_enrollment)

                # 3. Enroll in all implementation packages
                impl_pkg_items = (
                    self.db.query(BundleImplementationPackageItem)
                    .filter(BundleImplementationPackageItem.bundle_id == package.id)
                    .all()
                )

                for impl_item in impl_pkg_items:
                    impl_enrollment = self._create_impl_package_enrollment(
                        user.id,
                        impl_item.implementation_package_id,
                        order.id,
                        access_duration_days=impl_item.access_duration_days,
                    )
                    if impl_enrollment:
                        enrollments.append(impl_enrollment)
            else:
                # Regular package: enroll directly
                enrollment = self._create_single_enrollment(user.id, package.id, order.id)
                if enrollment:
                    enrollments.append(enrollment)

        return enrollments

    def _create_single_enrollment(
        self, user_id: uuid.UUID, package_id: uuid.UUID, order_id: uuid.UUID
    ) -> PackageEnrollment | None:
        """
        Create a single enrollment, checking for duplicates.

        Returns None if enrollment already exists.
        """
        # Check if enrollment already exists
        existing = (
            self.db.query(PackageEnrollment)
            .filter(
                PackageEnrollment.user_id == user_id,
                PackageEnrollment.package_id == package_id,
            )
            .first()
        )

        if existing:
            return None

        enrollment = PackageEnrollment(
            id=uuid.uuid4(),
            user_id=user_id,
            package_id=package_id,
            order_id=order_id,
            enrolled_at=datetime.now(UTC),
        )

        self.db.add(enrollment)
        return enrollment

    def _create_impl_package_enrollment(
        self,
        user_id: uuid.UUID,
        implementation_package_id: uuid.UUID,
        order_id: uuid.UUID,
        access_duration_days: int | None = None,
    ) -> ImplementationPackageEnrollment | None:
        """Create an ImplementationPackage enrollment, checking for duplicates."""
        existing = (
            self.db.query(ImplementationPackageEnrollment)
            .filter(
                ImplementationPackageEnrollment.user_id == user_id,
                ImplementationPackageEnrollment.package_id == implementation_package_id,
            )
            .first()
        )

        if existing:
            return None

        expires_at = None
        if access_duration_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=access_duration_days)

        enrollment = ImplementationPackageEnrollment(
            id=uuid.uuid4(),
            user_id=user_id,
            package_id=implementation_package_id,
            order_id=order_id,
            enrolled_at=datetime.now(UTC),
            expires_at=expires_at,
        )

        self.db.add(enrollment)
        return enrollment
