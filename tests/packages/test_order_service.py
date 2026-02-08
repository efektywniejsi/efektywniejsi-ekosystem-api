"""
Tests for OrderService - user creation and enrollment management.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core.security import get_password_hash
from app.packages.models.order import Order, OrderItem, OrderStatus, PaymentProvider
from app.packages.models.package import Package
from app.packages.services.order_service import OrderService


def create_test_package(db: Session, title: str = "Test Package") -> Package:
    """Create a test package."""
    package = Package(
        id=uuid.uuid4(),
        slug=f"test-package-{uuid.uuid4().hex[:8]}",
        title=title,
        description="Test package description",
        category="productivity",
        price=9900,
        difficulty="beginner",
        tools="[]",
        is_published=True,
        is_bundle=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(package)
    db.flush()
    return package


def create_test_order(
    db: Session,
    email: str,
    name: str,
    package: Package,
    webhook_processed: bool = False,
) -> Order:
    """Create a test order with one item."""
    order = Order(
        id=uuid.uuid4(),
        order_number=f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
        email=email,
        name=name,
        status=OrderStatus.PENDING,
        subtotal=package.price,
        total=package.price,
        currency="PLN",
        payment_provider=PaymentProvider.STRIPE,
        payment_intent_id=f"pi_{uuid.uuid4().hex}",
        webhook_processed=webhook_processed,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        id=uuid.uuid4(),
        order_id=order.id,
        package_id=package.id,
        package_title=package.title,
        package_slug=package.slug,
        price=package.price,
        created_at=datetime.now(UTC),
    )
    db.add(order_item)
    db.flush()

    db.refresh(order)
    return order


def create_user_without_password(db: Session, email: str, name: str) -> User:
    """Create a user with unusable password (simulating post-purchase state)."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        name=name,
        hashed_password="!",  # Unusable password
        role="paid",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    return user


def create_user_with_password(db: Session, email: str, name: str) -> User:
    """Create a user with a real password set."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        name=name,
        hashed_password=get_password_hash("securepassword123"),
        role="paid",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    return user


class TestOrderServiceProcessSuccessfulPayment:
    """Tests for OrderService.process_successful_payment()"""

    @pytest.mark.asyncio
    async def test_creates_new_user_with_reset_token(self, db_session: Session):
        """New user should be created with unusable password and reset token."""
        package = create_test_package(db_session)
        order = create_test_order(
            db_session,
            email="newuser@example.com",
            name="New User",
            package=package,
        )

        service = OrderService(db_session)
        result = await service.process_successful_payment(order)

        assert result["status"] == "success"
        assert result["is_new_user"] is True
        assert result["reset_token"] is not None
        assert len(result["reset_token"]) > 20  # Token should be substantial

        user = result["user"]
        assert user.email == "newuser@example.com"
        assert user.hashed_password == "!"
        assert user.password_reset_token is not None
        assert user.password_reset_token_expires is not None

    @pytest.mark.asyncio
    async def test_existing_user_with_password_gets_no_reset_token(self, db_session: Session):
        """Existing user with password should not receive a reset token."""
        package = create_test_package(db_session)
        existing_user = create_user_with_password(
            db_session,
            email="existing@example.com",
            name="Existing User",
        )
        order = create_test_order(
            db_session,
            email=existing_user.email,
            name=existing_user.name,
            package=package,
        )

        service = OrderService(db_session)
        result = await service.process_successful_payment(order)

        assert result["status"] == "success"
        assert result["is_new_user"] is False
        assert result["reset_token"] is None
        assert result["user"].id == existing_user.id

    @pytest.mark.asyncio
    async def test_existing_user_without_password_gets_new_reset_token(self, db_session: Session):
        """
        BUG FIX TEST: Existing user who never set password should get a NEW reset token.

        This was the bug - previously, returning users with hashed_password="!"
        would have is_new_user=True but reset_token=None, causing broken email links.
        """
        package = create_test_package(db_session)
        # User created from previous purchase but never set password
        existing_user = create_user_without_password(
            db_session,
            email="returning@example.com",
            name="Returning User",
        )
        original_user_id = existing_user.id

        order = create_test_order(
            db_session,
            email=existing_user.email,
            name=existing_user.name,
            package=package,
        )

        service = OrderService(db_session)
        result = await service.process_successful_payment(order)

        assert result["status"] == "success"
        assert result["is_new_user"] is True  # Still true because password == "!"
        assert result["reset_token"] is not None  # THIS IS THE FIX
        assert len(result["reset_token"]) > 20

        user = result["user"]
        assert user.id == original_user_id  # Same user, not a new one
        assert user.password_reset_token is not None
        assert user.password_reset_token_expires is not None

    @pytest.mark.asyncio
    async def test_idempotency_prevents_duplicate_processing(self, db_session: Session):
        """Already processed order should return early without changes."""
        package = create_test_package(db_session)
        order = create_test_order(
            db_session,
            email="idempotent@example.com",
            name="Idempotent User",
            package=package,
            webhook_processed=True,  # Already processed
        )

        service = OrderService(db_session)
        result = await service.process_successful_payment(order)

        assert result["status"] == "already_processed"
        assert result["user"] is None
        assert result["enrollments"] == []

    @pytest.mark.asyncio
    async def test_order_status_updated_after_processing(self, db_session: Session):
        """Order should be marked as completed after processing."""
        package = create_test_package(db_session)
        order = create_test_order(
            db_session,
            email="status@example.com",
            name="Status User",
            package=package,
        )

        service = OrderService(db_session)
        await service.process_successful_payment(order)

        assert order.status == OrderStatus.COMPLETED
        assert order.webhook_processed is True
        assert order.payment_completed_at is not None
        assert order.user_id is not None

    @pytest.mark.asyncio
    async def test_enrollment_created_for_package(self, db_session: Session):
        """Enrollment should be created linking user to purchased package."""
        package = create_test_package(db_session, title="Premium Package")
        order = create_test_order(
            db_session,
            email="enroll@example.com",
            name="Enroll User",
            package=package,
        )

        service = OrderService(db_session)
        result = await service.process_successful_payment(order)

        enrollments = result["enrollments"]
        assert len(enrollments) == 1
        assert enrollments[0].package_id == package.id
        assert enrollments[0].user_id == result["user"].id
        assert enrollments[0].order_id == order.id


class TestOrderServiceGetOrCreateUser:
    """Tests for OrderService._get_or_create_user() internal method."""

    def test_creates_user_when_not_exists(self, db_session: Session):
        """Should create new user when email doesn't exist."""
        package = create_test_package(db_session)
        order = create_test_order(
            db_session,
            email="brand_new@example.com",
            name="Brand New",
            package=package,
        )

        service = OrderService(db_session)
        user = service._get_or_create_user(order)

        assert user.email == "brand_new@example.com"
        assert user.name == "Brand New"
        assert user.hashed_password == "!"
        assert user.role == "paid"
        assert user.is_active is True
        assert hasattr(user, "_raw_reset_token")
        assert user._raw_reset_token is not None

    def test_returns_existing_user_with_password(self, db_session: Session):
        """Should return existing user without modification when password is set."""
        existing = create_user_with_password(
            db_session,
            email="has_password@example.com",
            name="Has Password",
        )
        original_password_hash = existing.hashed_password

        package = create_test_package(db_session)
        order = create_test_order(
            db_session,
            email=existing.email,
            name=existing.name,
            package=package,
        )

        service = OrderService(db_session)
        user = service._get_or_create_user(order)

        assert user.id == existing.id
        assert user.hashed_password == original_password_hash
        assert not hasattr(user, "_raw_reset_token") or user._raw_reset_token is None

    def test_generates_token_for_existing_user_without_password(self, db_session: Session):
        """Should generate new reset token for existing user with unusable password."""
        existing = create_user_without_password(
            db_session,
            email="no_password@example.com",
            name="No Password",
        )

        package = create_test_package(db_session)
        order = create_test_order(
            db_session,
            email=existing.email,
            name=existing.name,
            package=package,
        )

        service = OrderService(db_session)
        user = service._get_or_create_user(order)

        assert user.id == existing.id
        assert user.hashed_password == "!"
        assert user.password_reset_token is not None
        assert user.password_reset_token_expires is not None
        assert hasattr(user, "_raw_reset_token")
        assert user._raw_reset_token is not None
