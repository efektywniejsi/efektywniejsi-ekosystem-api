"""Fixtures for storage tests that don't require testcontainers.

These fixtures provide isolated database sessions using SQLite in-memory
for fast unit testing without Docker dependencies.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base


@pytest.fixture
def memory_engine():
    """Create an in-memory SQLite engine for isolated testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(memory_engine):
    """Create a database session for testing.

    This overrides the global db_session fixture from conftest.py
    to use SQLite in-memory instead of testcontainers.
    """
    session_factory = sessionmaker(bind=memory_engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_storage():
    """Mock storage backend for testing."""
    storage = MagicMock()
    storage.list_objects.return_value = []
    storage.delete.return_value = None
    return storage


# Fixtures for API tests - mock the heavy dependencies


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.ping.return_value = True
    return redis


@pytest.fixture
def admin_user_data():
    """Admin user data for token creation."""
    return {
        "id": str(uuid.uuid4()),
        "email": "admin@test.com",
        "role": "admin",
    }


@pytest.fixture
def regular_user_data():
    """Regular user data for token creation."""
    return {
        "id": str(uuid.uuid4()),
        "email": "user@test.com",
        "role": "paid",
    }


@pytest.fixture
def test_admin_token(admin_user_data):
    """Generate admin JWT token without database."""
    from app.core.security import create_access_token

    return create_access_token(
        {"sub": admin_user_data["id"], "email": admin_user_data["email"], "role": "admin"}
    )


@pytest.fixture
def test_user_token(regular_user_data):
    """Generate regular user JWT token without database."""
    from app.core.security import create_access_token

    return create_access_token(
        {"sub": regular_user_data["id"], "email": regular_user_data["email"], "role": "paid"}
    )


@pytest.fixture
async def test_client(db_session, mock_redis, admin_user_data, regular_user_data):
    """Create test client with mocked dependencies."""
    from httpx import ASGITransport, AsyncClient

    from app.core import redis as redis_module
    from app.db.session import get_db
    from app.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    redis_module.redis_client = mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
