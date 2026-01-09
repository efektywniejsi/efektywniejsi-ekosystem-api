import uuid
from datetime import datetime

from faker import Faker
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core.security import get_password_hash

fake = Faker()


def create_user_factory(
    db_session: Session,
    email: str | None = None,
    password: str = "testpass123",
    name: str | None = None,
    role: str = "paid",
    is_active: bool = True,
) -> User:
    """
    Factory function to create test users.

    Args:
        db_session: Database session
        email: User email (generates random if None)
        password: Plain text password
        name: User name (generates random if None)
        role: User role ("paid" or "admin")
        is_active: Whether user is active

    Returns:
        Created User instance
    """
    user = User(
        id=uuid.uuid4(),
        email=email or fake.email(),
        hashed_password=get_password_hash(password),
        name=name or fake.name(),
        role=role,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user
