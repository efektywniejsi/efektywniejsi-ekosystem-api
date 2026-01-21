"""
Order service for user creation and enrollment management.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core.security import generate_reset_token
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
            is_new_user = user.hashed_password == ""

            # 3. Create enrollments
            enrollments = await self._create_enrollments(order, user)

            # 4. Update order
            order.user_id = user.id
            order.status = OrderStatus.COMPLETED
            order.payment_completed_at = datetime.utcnow()
            order.webhook_processed = True

            self.db.commit()

            return {
                "status": "success",
                "user": user,
                "order": order,
                "enrollments": enrollments,
                "is_new_user": is_new_user,
                "reset_token": user.password_reset_token if is_new_user else None,
            }

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to process payment: {e}") from e

    def _get_or_create_user(self, order: Order) -> User:
        """Get existing user or create a new one."""
        # Check if user exists
        user = self.db.query(User).filter(User.email == order.email).first()

        if user:
            return user

        # Create new user with unusable password
        raw_token, hashed_token, expiry = generate_reset_token()

        user = User(
            id=uuid.uuid4(),
            email=order.email,
            name=order.name,
            hashed_password="",  # Unusable - forces password reset
            role="paid",
            is_active=True,
            password_reset_token=hashed_token,
            password_reset_token_expires=expiry,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(user)
        self.db.flush()  # Get user.id

        # Store raw token temporarily for email (it's already in user object as hashed)
        # The raw token needs to be passed back for email
        user.password_reset_token = raw_token  # type: ignore  # Temporarily store raw token

        return user

    async def _create_enrollments(self, order: Order, user: User) -> list[PackageEnrollment]:
        """
        Create package enrollments from order items.

        Handles bundle packages by enrolling in child packages instead.
        """
        enrollments = []

        for order_item in order.items:
            package = self.db.query(Package).filter(Package.id == order_item.package_id).first()

            if not package:
                continue

            if package.is_bundle:
                # Bundle: enroll in all child packages
                for bundle_item in package.bundle_items:
                    enrollment = self._create_single_enrollment(
                        user.id, bundle_item.child_package_id, order.id
                    )
                    if enrollment:
                        enrollments.append(enrollment)
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
            enrolled_at=datetime.utcnow(),
        )

        self.db.add(enrollment)
        return enrollment
