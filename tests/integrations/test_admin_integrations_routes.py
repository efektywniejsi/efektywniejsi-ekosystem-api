"""
Tests for admin integrations routes.
"""

import pytest
from httpx import AsyncClient


class TestAdminListIntegrations:
    """Tests for GET /api/v1/admin/integrations"""

    @pytest.mark.asyncio
    async def test_admin_list_includes_unpublished(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
        test_integration_unpublished,
    ):
        """Test that admin can see all integrations including unpublished."""
        response = await test_client.get(
            "/api/v1/admin/integrations",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        slugs = [i["slug"] for i in data]

        assert test_integration.slug in slugs
        assert test_integration_unpublished.slug in slugs

    @pytest.mark.asyncio
    async def test_admin_list_requires_admin_role(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test that regular users cannot access admin endpoint."""
        response = await test_client.get(
            "/api/v1/admin/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 403


class TestAdminCreateIntegration:
    """Tests for POST /api/v1/admin/integrations"""

    @pytest.mark.asyncio
    async def test_create_integration(
        self,
        test_client: AsyncClient,
        test_admin_token,
    ):
        """Test creating a new integration."""
        payload = {
            "slug": "new-integration",
            "name": "New Integration",
            "icon": "Star",
            "category": "AI",
            "description": "A brand new integration for testing.",
            "auth_guide": "# Setup\n1. Create account",
            "official_docs_url": "https://example.com/docs",
            "video_tutorial_url": "https://youtube.com/watch?v=abc",
            "is_published": True,
            "sort_order": 10,
            "integration_types": ["API", "OAuth 2.0"],
        }

        response = await test_client.post(
            "/api/v1/admin/integrations",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["slug"] == "new-integration"
        assert data["name"] == "New Integration"
        assert data["category"] == "AI"
        assert data["is_published"] is True
        assert "API" in data["integration_types"]
        assert "OAuth 2.0" in data["integration_types"]

    @pytest.mark.asyncio
    async def test_create_integration_duplicate_slug(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
    ):
        """Test that duplicate slug returns error."""
        payload = {
            "slug": test_integration.slug,  # Duplicate
            "name": "Another Integration",
            "icon": "Star",
            "category": "AI",
            "description": "Duplicate slug test.",
            "integration_types": [],
        }

        response = await test_client.post(
            "/api/v1/admin/integrations",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 400
        assert "slug" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_integration_invalid_url(
        self,
        test_client: AsyncClient,
        test_admin_token,
    ):
        """Test that invalid URL returns validation error."""
        payload = {
            "slug": "invalid-url-test",
            "name": "Invalid URL Test",
            "icon": "Star",
            "category": "AI",
            "description": "Testing invalid URL.",
            "official_docs_url": "not-a-valid-url",
            "integration_types": [],
        }

        response = await test_client.post(
            "/api/v1/admin/integrations",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_integration_requires_admin(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test that regular users cannot create integrations."""
        payload = {
            "slug": "user-attempt",
            "name": "User Attempt",
            "icon": "Star",
            "category": "AI",
            "description": "Should fail.",
            "integration_types": [],
        }

        response = await test_client.post(
            "/api/v1/admin/integrations",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 403


class TestAdminUpdateIntegration:
    """Tests for PATCH /api/v1/admin/integrations/{id}"""

    @pytest.mark.asyncio
    async def test_update_integration(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
    ):
        """Test updating an integration."""
        payload = {
            "name": "Updated Name",
            "description": "Updated description.",
            "is_published": False,
        }

        response = await test_client.patch(
            f"/api/v1/admin/integrations/{test_integration.id}",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description."
        assert data["is_published"] is False
        # Slug should remain unchanged
        assert data["slug"] == test_integration.slug

    @pytest.mark.asyncio
    async def test_update_integration_types(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
    ):
        """Test updating integration types."""
        payload = {
            "integration_types": ["MCP"],
        }

        response = await test_client.patch(
            f"/api/v1/admin/integrations/{test_integration.id}",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["integration_types"] == ["MCP"]

    @pytest.mark.asyncio
    async def test_update_integration_not_found(
        self,
        test_client: AsyncClient,
        test_admin_token,
    ):
        """Test 404 for non-existent integration."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await test_client.patch(
            f"/api/v1/admin/integrations/{fake_id}",
            json={"name": "Updated"},
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 404


class TestAdminDeleteIntegration:
    """Tests for DELETE /api/v1/admin/integrations/{id}"""

    @pytest.mark.asyncio
    async def test_delete_integration(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration_unpublished,
    ):
        """Test deleting an integration."""
        response = await test_client.delete(
            f"/api/v1/admin/integrations/{test_integration_unpublished.id}",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await test_client.get(
            f"/api/v1/admin/integrations/{test_integration_unpublished.id}",
            cookies={"access_token": test_admin_token},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_integration_not_found(
        self,
        test_client: AsyncClient,
        test_admin_token,
    ):
        """Test 404 for deleting non-existent integration."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await test_client.delete(
            f"/api/v1/admin/integrations/{fake_id}",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 404


class TestAdminLessonIntegrations:
    """Tests for lesson integration management."""

    @pytest.mark.asyncio
    async def test_attach_integration_to_lesson(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
        test_course_with_lesson,
    ):
        """Test attaching an integration to a lesson."""
        _, _, lesson = test_course_with_lesson

        payload = {
            "integration_id": str(test_integration.id),
            "context_note": "Use this for AI features",
            "sort_order": 0,
        }

        response = await test_client.post(
            f"/api/v1/admin/lessons/{lesson.id}/integrations",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["integration"]["slug"] == test_integration.slug
        assert data["context_note"] == "Use this for AI features"

    @pytest.mark.asyncio
    async def test_attach_integration_already_attached(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
        test_course_with_lesson,
        test_lesson_integration,
    ):
        """Test that attaching same integration twice returns error."""
        _, _, lesson = test_course_with_lesson

        payload = {
            "integration_id": str(test_integration.id),
        }

        response = await test_client.post(
            f"/api/v1/admin/lessons/{lesson.id}/integrations",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 400
        assert "już przypisana" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_detach_integration_from_lesson(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
        test_course_with_lesson,
        test_lesson_integration,
    ):
        """Test detaching an integration from a lesson."""
        _, _, lesson = test_course_with_lesson

        response = await test_client.delete(
            f"/api/v1/admin/lessons/{lesson.id}/integrations/{test_integration.id}",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 204

        # Verify it's detached
        get_response = await test_client.get(
            f"/api/v1/lessons/{lesson.id}/integrations",
            cookies={"access_token": test_admin_token},
        )
        assert get_response.status_code == 200
        assert get_response.json() == []

    @pytest.mark.asyncio
    async def test_detach_not_attached_returns_404(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_integration,
        test_course_with_lesson,
    ):
        """Test detaching a non-attached integration returns 404."""
        _, _, lesson = test_course_with_lesson

        response = await test_client.delete(
            f"/api/v1/admin/lessons/{lesson.id}/integrations/{test_integration.id}",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_attach_requires_admin(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration,
        test_course_with_lesson,
    ):
        """Test that regular users cannot attach integrations."""
        _, _, lesson = test_course_with_lesson

        payload = {
            "integration_id": str(test_integration.id),
        }

        response = await test_client.post(
            f"/api/v1/admin/lessons/{lesson.id}/integrations",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 403
