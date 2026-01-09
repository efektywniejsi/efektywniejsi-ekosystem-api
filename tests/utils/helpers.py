from typing import Any

from jose import jwt

from app.core.config import settings


def assert_token_response_valid(data: dict[str, Any]) -> None:
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "user" in data


def assert_user_response_valid(data: dict[str, Any]) -> None:
    assert "id" in data
    assert "email" in data
    assert "name" in data
    assert "role" in data


def create_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def decode_jwt_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
