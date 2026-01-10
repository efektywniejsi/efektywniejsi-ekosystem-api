from pathlib import Path

from dotenv import load_dotenv

env_file = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_file)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from testcontainers.core.container import DockerContainer  # noqa: E402
from testcontainers.core.waiting_utils import wait_for_logs  # noqa: E402
from testcontainers.redis import RedisContainer  # noqa: E402

from app.core import redis as redis_module  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import (  # noqa: E402
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from tests.utils.factories import create_user_factory  # noqa: E402


@pytest.fixture(scope="session")
def postgres_container():
    container = DockerContainer("postgres:16")
    container.with_exposed_ports(5432)
    container.with_env("POSTGRES_USER", "test")
    container.with_env("POSTGRES_PASSWORD", "test")
    container.with_env("POSTGRES_DB", "test")

    container.start()
    wait_for_logs(container, "database system is ready to accept connections", timeout=30)

    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7") as redis:
        yield redis


@pytest.fixture(scope="session")
def test_database_url(postgres_container):
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = "test"
    password = "test"
    dbname = "test"

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    engine = create_engine(test_database_url)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_local(test_engine):
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture
def db_session(test_session_local):
    session = test_session_local()

    session.commit = session.flush

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def test_redis_url(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture
async def redis_client(test_redis_url):
    client = Redis.from_url(test_redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.close()


@pytest.fixture
async def test_app(db_session, redis_client):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    redis_module.redis_client = redis_client

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
async def test_client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user(db_session):
    return create_user_factory(
        db_session, email="test@example.com", password="testpass123", role="paid"
    )


@pytest.fixture
def test_admin(db_session):
    return create_user_factory(
        db_session, email="admin@example.com", password="adminpass123", role="admin"
    )


@pytest.fixture
def test_user_token(test_user):
    return create_access_token(
        {"sub": str(test_user.id), "email": test_user.email, "role": test_user.role}
    )


@pytest.fixture
def test_admin_token(test_admin):
    return create_access_token(
        {"sub": str(test_admin.id), "email": test_admin.email, "role": test_admin.role}
    )


@pytest.fixture
async def test_refresh_token(test_user, redis_client):
    token = create_refresh_token(
        {"sub": str(test_user.id), "email": test_user.email, "role": test_user.role}
    )

    token_hash = hash_token(token)
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis_module.store_refresh_token(token_hash, str(test_user.id), ttl_seconds)

    return token
