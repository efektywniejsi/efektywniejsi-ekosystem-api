"""
Tests for public integrations routes.
"""

import pytest
from httpx import AsyncClient


class TestListIntegrations:
    """Tests for GET /api/v1/integrations"""

    @pytest.mark.asyncio
    async def test_list_integrations_returns_published_only(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration,
        test_integration_unpublished,
    ):
        """Test that only published integrations are returned."""
        response = await test_client.get(
            "/api/v1/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()
        slugs = [i["slug"] for i in data]

        assert test_integration.slug in slugs
        assert test_integration_unpublished.slug not in slugs

    @pytest.mark.asyncio
    async def test_list_integrations_includes_types(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration,
    ):
        """Test that integration types are included in response."""
        response = await test_client.get(
            "/api/v1/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        integration = next(i for i in data if i["slug"] == test_integration.slug)
        assert "API" in integration["integration_types"]
        assert "MCP" in integration["integration_types"]

    @pytest.mark.asyncio
    async def test_list_integrations_filter_by_category(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integrations_list,
    ):
        """Test filtering integrations by category."""
        response = await test_client.get(
            "/api/v1/integrations",
            params={"category": "CRM"},
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["slug"] == "hubspot"
        assert data[0]["category"] == "CRM"

    @pytest.mark.asyncio
    async def test_list_integrations_search(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integrations_list,
    ):
        """Test searching integrations by name/description."""
        response = await test_client.get(
            "/api/v1/integrations",
            params={"search": "payment"},
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["slug"] == "stripe"

    @pytest.mark.asyncio
    async def test_list_integrations_requires_auth(
        self,
        test_client: AsyncClient,
        test_integration,
    ):
        """Test that listing integrations requires authentication."""
        response = await test_client.get("/api/v1/integrations")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_integrations_includes_usage_count(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration,
        test_lesson_integration,
    ):
        """Test that usage count is included in response."""
        response = await test_client.get(
            "/api/v1/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        integration = next(i for i in data if i["slug"] == test_integration.slug)
        assert integration["usage_count"] == 1


class TestGetIntegration:
    """Tests for GET /api/v1/integrations/{slug}"""

    @pytest.mark.asyncio
    async def test_get_integration_by_slug(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration,
    ):
        """Test getting integration details by slug."""
        response = await test_client.get(
            f"/api/v1/integrations/{test_integration.slug}",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["slug"] == test_integration.slug
        assert data["name"] == test_integration.name
        assert data["category"] == test_integration.category
        assert data["auth_guide"] is not None
        assert "integration_types" in data

    @pytest.mark.asyncio
    async def test_get_integration_includes_lessons(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration,
        test_lesson_integration,
        test_course_with_lesson,
    ):
        """Test that used_in_lessons is included in detail response."""
        _, _, lesson = test_course_with_lesson

        response = await test_client.get(
            f"/api/v1/integrations/{test_integration.slug}",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "used_in_lessons" in data
        assert len(data["used_in_lessons"]) == 1
        assert data["used_in_lessons"][0]["id"] == str(lesson.id)

    @pytest.mark.asyncio
    async def test_get_integration_not_found(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test 404 for non-existent integration."""
        response = await test_client.get(
            "/api/v1/integrations/non-existent-slug",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_unpublished_integration_returns_404(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration_unpublished,
    ):
        """Test that unpublished integrations return 404 for regular users."""
        response = await test_client.get(
            f"/api/v1/integrations/{test_integration_unpublished.slug}",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 404


class TestGetCategories:
    """Tests for GET /api/v1/integrations/categories"""

    @pytest.mark.asyncio
    async def test_get_categories_with_counts(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integrations_list,
    ):
        """Test getting categories with counts."""
        response = await test_client.get(
            "/api/v1/integrations/categories",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        categories = {c["category"]: c["count"] for c in data}
        assert categories["CRM"] == 1
        assert categories["Communication"] == 1
        assert categories["Payments"] == 1

    @pytest.mark.asyncio
    async def test_get_categories_excludes_unpublished(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_integration_unpublished,
    ):
        """Test that unpublished integrations don't count in categories."""
        response = await test_client.get(
            "/api/v1/integrations/categories",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Tools category should not appear (only unpublished)
        categories = [c["category"] for c in data]
        assert "Tools" not in categories


class TestGetLessonIntegrations:
    """Tests for GET /api/v1/lessons/{lesson_id}/integrations"""

    @pytest.mark.asyncio
    async def test_get_lesson_integrations(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_lesson_integration,
        test_course_with_lesson,
        test_integration,
    ):
        """Test getting integrations attached to a lesson."""
        _, _, lesson = test_course_with_lesson

        response = await test_client.get(
            f"/api/v1/lessons/{lesson.id}/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["integration"]["slug"] == test_integration.slug
        assert data[0]["context_note"] is not None

    @pytest.mark.asyncio
    async def test_get_lesson_integrations_not_found(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test 404 for non-existent lesson."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await test_client.get(
            f"/api/v1/lessons/{fake_id}/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_lesson_integrations_empty(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_course_with_lesson,
    ):
        """Test getting empty list when no integrations attached."""
        _, _, lesson = test_course_with_lesson

        response = await test_client.get(
            f"/api/v1/lessons/{lesson.id}/integrations",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []
