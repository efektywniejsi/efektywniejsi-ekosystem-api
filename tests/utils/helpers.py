from typing import Any

import httpx
from jose import jwt

from app.core.config import settings


def assert_token_response_valid(
    data: dict[str, Any], response: httpx.Response | None = None
) -> None:
    """Assert that login response is valid.

    Since tokens are now in httpOnly cookies, we check for user data in JSON
    and optionally verify cookies are set in the response.
    """
    assert "user" in data

    if response is not None:
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies


def assert_user_response_valid(data: dict[str, Any]) -> None:
    assert "id" in data
    assert "email" in data
    assert "name" in data
    assert "role" in data


def create_auth_headers(token: str) -> dict[str, str]:
    """Create Authorization headers with Bearer token.

    Note: This is deprecated since auth now uses httpOnly cookies.
    Tests should rely on the test_client's automatic cookie handling instead.
    """
    return {"Authorization": f"Bearer {token}"}


def extract_token_from_cookie(response: httpx.Response, cookie_name: str) -> str:
    """Extract JWT token from response cookies."""
    cookies = response.cookies
    token = cookies.get(cookie_name)
    if not token:
        raise ValueError(f"Cookie {cookie_name} not found in response")
    return token


def decode_jwt_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def set_auth_cookies(client: httpx.AsyncClient, access_token: str, refresh_token: str) -> None:
    """Set authentication cookies on the test client."""
    client.cookies.set("access_token", access_token)
    client.cookies.set("refresh_token", refresh_token)


def set_access_token_cookie(client: httpx.AsyncClient, access_token: str) -> None:
    """Set only the access token cookie on the test client."""
    client.cookies.set("access_token", access_token)
