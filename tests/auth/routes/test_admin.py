import pytest

from tests.utils.factories import create_user_factory
from tests.utils.helpers import assert_user_response_valid, set_access_token_cookie


class TestCreateUserEndpoint:
    @pytest.mark.asyncio
    async def test_should_create_user_when_admin(self, test_client, test_admin_token, db_session):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "Password123",
            "role": "paid",
            "send_welcome_email": False,
        }

        response = await test_client.post("/api/v1/admin/users", json=payload)

        assert response.status_code == 201
        data = response.json()

        assert_user_response_valid(data)
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["role"] == "paid"

    @pytest.mark.asyncio
    async def test_should_return_409_when_email_already_exists(
        self, test_client, test_admin_token, test_user
    ):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {
            "email": test_user.email,
            "name": "Duplicate User",
            "password": "Password123",
            "role": "paid",
        }

        response = await test_client.post("/api/v1/admin/users", json=payload)

        assert response.status_code == 409
        assert "już zarejestrowany" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_422_when_password_too_short(self, test_client, test_admin_token):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "short",
            "role": "paid",
        }

        response = await test_client.post("/api/v1/admin/users", json=payload)

        assert response.status_code == 422
        assert "co najmniej 8 znaków" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_403_when_not_admin(self, test_client, test_user_token):
        set_access_token_cookie(test_client, test_user_token)
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "Password123",
            "role": "paid",
        }

        response = await test_client.post("/api/v1/admin/users", json=payload)

        assert response.status_code == 403
        assert "Wymagane uprawnienia administratora" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_401_when_not_authenticated(self, test_client):
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "Password123",
            "role": "paid",
        }

        response = await test_client.post("/api/v1/admin/users", json=payload)

        assert response.status_code == 401


class TestListUsersEndpoint:
    @pytest.mark.asyncio
    async def test_should_return_all_users_when_admin(
        self, test_client, test_admin_token, test_user, test_admin
    ):
        set_access_token_cookie(test_client, test_admin_token)

        response = await test_client.get("/api/v1/admin/users")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "users" in data
        assert data["total"] >= 2
        assert len(data["users"]) >= 2

    @pytest.mark.asyncio
    async def test_should_support_pagination(
        self, test_client, test_admin_token, db_session, test_user, test_admin
    ):
        for i in range(5):
            create_user_factory(db_session, email=f"user{i}@example.com")

        set_access_token_cookie(test_client, test_admin_token)

        response = await test_client.get("/api/v1/admin/users?skip=0&limit=3")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 7
        assert len(data["users"]) == 3

    @pytest.mark.asyncio
    async def test_should_filter_by_role(
        self, test_client, test_admin_token, test_user, test_admin, db_session
    ):
        create_user_factory(db_session, email="paid1@example.com", role="paid")
        create_user_factory(db_session, email="paid2@example.com", role="paid")

        set_access_token_cookie(test_client, test_admin_token)

        response = await test_client.get("/api/v1/admin/users?role=admin")

        assert response.status_code == 200
        data = response.json()

        assert all(user["role"] == "admin" for user in data["users"])

    @pytest.mark.asyncio
    async def test_should_filter_by_active_status(
        self, test_client, test_admin_token, db_session, test_user
    ):
        create_user_factory(db_session, email="inactive@example.com", is_active=False)

        set_access_token_cookie(test_client, test_admin_token)

        response = await test_client.get("/api/v1/admin/users?is_active=false")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_should_return_403_when_not_admin(self, test_client, test_user_token):
        set_access_token_cookie(test_client, test_user_token)

        response = await test_client.get("/api/v1/admin/users")

        assert response.status_code == 403


class TestUpdateUserEndpoint:
    @pytest.mark.asyncio
    async def test_should_update_user_name_when_admin(
        self, test_client, test_admin_token, test_user
    ):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {"name": "Updated Name"}

        response = await test_client.patch(f"/api/v1/admin/users/{test_user.id}", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_should_update_user_role_when_admin(
        self, test_client, test_admin_token, test_user
    ):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {"role": "admin"}

        response = await test_client.patch(f"/api/v1/admin/users/{test_user.id}", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_should_update_active_status_when_admin(
        self, test_client, test_admin_token, test_user
    ):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {"is_active": False}

        response = await test_client.patch(f"/api/v1/admin/users/{test_user.id}", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_should_return_404_when_user_not_found(self, test_client, test_admin_token):
        set_access_token_cookie(test_client, test_admin_token)
        payload = {"name": "Updated Name"}
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        response = await test_client.patch(f"/api/v1/admin/users/{fake_uuid}", json=payload)

        assert response.status_code == 404
        assert "nie znaleziony" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_should_return_403_when_not_admin(self, test_client, test_user_token, test_user):
        set_access_token_cookie(test_client, test_user_token)
        payload = {"name": "Updated Name"}

        response = await test_client.patch(f"/api/v1/admin/users/{test_user.id}", json=payload)

        assert response.status_code == 403
