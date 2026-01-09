import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class User(Base):
    """
    User model for authentication and authorization.

    Attributes:
        id: Unique UUID primary key
        email: Unique email address (indexed for fast lookups)
        hashed_password: Argon2 hashed password
        name: User's display name
        role: User role ("admin" or "paid")
        is_active: Whether the user account is active
        password_reset_token: SHA-256 hashed password reset token (nullable)
        password_reset_token_expires: Expiry datetime for reset token (nullable)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)

    # Role: "admin" or "paid"
    role = Column(String(50), nullable=False, default="paid")
    is_active = Column(Boolean, default=True, nullable=False)

    # Password reset fields
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_token_expires = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
