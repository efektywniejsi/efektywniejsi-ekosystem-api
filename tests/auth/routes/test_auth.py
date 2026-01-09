import pytest

from app.core import redis as redis_module
from app.core.security import hash_token
from tests.utils.factories import create_user_factory
from tests.utils.helpers import (
    assert_token_response_valid,
    assert_user_response_valid,
    create_auth_headers,
)


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_should_return_tokens_when_valid_credentials(
        self, test_client, test_user, redis_client
    ):
        payload = {"email": test_user.email, "password": "testpass123", "role": "paid"}

        response = await test_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert_token_response_valid(data)
        assert data["user"]["email"] == test_user.email
        assert data["user"]["role"] == "paid"
        assert data["user"]["id"] == str(test_user.id)

        # Verify refresh token stored in Redis
        token_hash = hash_token(data["refresh_token"])
        token_data = await redis_module.get_refresh_token(token_hash)
        assert token_data is not None
        assert token_data["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_should_return_tokens_for_admin(self, test_client, test_admin):
        payload = {"email": test_admin.email, "password": "adminpass123", "role": "admin"}

        response = await test_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == test_admin.email

    @pytest.mark.asyncio
    async def test_should_return_401_when_email_not_found(self, test_client):
        payload = {"email": "nonexistent@example.com", "password": "testpass123", "role": "paid"}

        response = await test_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_401_when_password_incorrect(self, test_client, test_user):
        payload = {"email": test_user.email, "password": "wrongpassword", "role": "paid"}

        response = await test_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_403_when_user_inactive(self, test_client, db_session):
        inactive_user = create_user_factory(
            db_session, email="inactive@example.com", password="testpass123", is_active=False
        )

        payload = {"email": inactive_user.email, "password": "testpass123", "role": "paid"}

        response = await test_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 403
        assert "Inactive user" in response.json()["detail"]


class TestRefreshEndpoint:
    @pytest.mark.asyncio
    async def test_should_return_new_access_token_when_valid_refresh_token(
        self, test_client, test_user, test_refresh_token
    ):
        payload = {"refresh_token": test_refresh_token}

        response = await test_client.post("/api/v1/auth/refresh", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_should_return_401_when_invalid_refresh_token(self, test_client):
        payload = {"refresh_token": "invalid-token"}

        response = await test_client.post("/api/v1/auth/refresh", json=payload)

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_401_when_refresh_token_revoked(
        self, test_client, test_refresh_token, redis_client
    ):
        # Revoke token
        token_hash = hash_token(test_refresh_token)
        await redis_module.revoke_refresh_token(token_hash)

        payload = {"refresh_token": test_refresh_token}

        response = await test_client.post("/api/v1/auth/refresh", json=payload)

        assert response.status_code == 401
        assert "revoked or expired" in response.json()["detail"]


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_should_revoke_refresh_token(
        self, test_client, test_user_token, test_refresh_token, redis_client
    ):
        # Verify token exists before logout
        token_hash = hash_token(test_refresh_token)
        token_data = await redis_module.get_refresh_token(token_hash)
        assert token_data is not None

        # Logout
        payload = {"refresh_token": test_refresh_token}
        headers = create_auth_headers(test_user_token)

        response = await test_client.post("/api/v1/auth/logout", json=payload, headers=headers)

        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

        # Verify token revoked
        token_data = await redis_module.get_refresh_token(token_hash)
        assert token_data is None

    @pytest.mark.asyncio
    async def test_should_return_403_when_no_auth_token(self, test_client, test_refresh_token):
        payload = {"refresh_token": test_refresh_token}

        response = await test_client.post("/api/v1/auth/logout", json=payload)

        assert response.status_code == 403


class TestMeEndpoint:
    @pytest.mark.asyncio
    async def test_should_return_user_info_when_authenticated(
        self, test_client, test_user, test_user_token
    ):
        headers = create_auth_headers(test_user_token)

        response = await test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert_user_response_valid(data)
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["role"] == test_user.role

    @pytest.mark.asyncio
    async def test_should_return_403_when_no_token(self, test_client):
        response = await test_client.get("/api/v1/auth/me")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_should_return_401_when_invalid_token(self, test_client):
        headers = create_auth_headers("invalid-token")

        response = await test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401
