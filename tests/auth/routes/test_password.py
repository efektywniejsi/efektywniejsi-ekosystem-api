from datetime import datetime, timedelta

import pytest

from app.core.security import generate_reset_token
from tests.utils.factories import create_user_factory


class TestRequestPasswordResetEndpoint:
    @pytest.mark.asyncio
    async def test_should_return_success_message_for_existing_user(self, test_client, test_user):
        payload = {"email": test_user.email}

        response = await test_client.post("/api/v1/password/request-reset", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "reset link has been sent" in data["message"]

    @pytest.mark.asyncio
    async def test_should_return_same_message_for_nonexistent_user(self, test_client):
        payload = {"email": "nonexistent@example.com"}

        response = await test_client.post("/api/v1/password/request-reset", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "reset link has been sent" in data["message"]

    @pytest.mark.asyncio
    async def test_should_return_same_message_for_inactive_user(self, test_client, db_session):
        inactive_user = create_user_factory(
            db_session, email="inactive@example.com", is_active=False
        )

        payload = {"email": inactive_user.email}

        response = await test_client.post("/api/v1/password/request-reset", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "reset link has been sent" in data["message"]


class TestResetPasswordEndpoint:
    @pytest.mark.asyncio
    async def test_should_reset_password_with_valid_token(self, test_client, test_user, db_session):
        raw_token, hashed_token, expiry = generate_reset_token()
        test_user.password_reset_token = hashed_token
        test_user.password_reset_token_expires = expiry
        db_session.commit()

        payload = {"token": raw_token, "new_password": "newSecurePassword123"}

        response = await test_client.post("/api/v1/password/reset", json=payload)

        assert response.status_code == 200
        assert "successfully reset" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_should_return_400_when_token_invalid(self, test_client):
        payload = {"token": "invalid-token", "new_password": "newPassword123"}

        response = await test_client.post("/api/v1/password/reset", json=payload)

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_400_when_token_expired(self, test_client, test_user, db_session):
        raw_token, hashed_token, _ = generate_reset_token()
        test_user.password_reset_token = hashed_token
        test_user.password_reset_token_expires = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        payload = {"token": raw_token, "new_password": "newPassword123"}

        response = await test_client.post("/api/v1/password/reset", json=payload)

        assert response.status_code == 400
        assert "expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_422_when_password_too_short(
        self, test_client, test_user, db_session
    ):
        raw_token, hashed_token, expiry = generate_reset_token()
        test_user.password_reset_token = hashed_token
        test_user.password_reset_token_expires = expiry
        db_session.commit()

        payload = {"token": raw_token, "new_password": "short"}

        response = await test_client.post("/api/v1/password/reset", json=payload)

        assert response.status_code == 422
        assert "at least 8 characters" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_allow_login_with_new_password(self, test_client, test_user, db_session):
        raw_token, hashed_token, expiry = generate_reset_token()
        test_user.password_reset_token = hashed_token
        test_user.password_reset_token_expires = expiry
        db_session.commit()

        new_password = "brandNewPassword123"
        reset_payload = {"token": raw_token, "new_password": new_password}
        await test_client.post("/api/v1/password/reset", json=reset_payload)

        login_payload = {"email": test_user.email, "password": new_password}
        response = await test_client.post("/api/v1/auth/login", json=login_payload)

        assert response.status_code == 200
        assert "access_token" in response.json()
