"""
Tests for integration proposals routes.
"""

import pytest
from httpx import AsyncClient


class TestSubmitProposal:
    """Tests for POST /api/v1/integration-proposals"""

    @pytest.mark.asyncio
    async def test_submit_proposal(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test submitting a new integration proposal."""
        payload = {
            "name": "Notion API",
            "category": "Productivity",
            "description": "Integration with Notion API for syncing notes and databases.",
            "official_docs_url": "https://developers.notion.com",
        }

        response = await test_client.post(
            "/api/v1/integration-proposals",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Notion API"
        assert data["category"] == "Productivity"
        assert data["status"] == "pending"
        assert data["official_docs_url"] == "https://developers.notion.com/"

    @pytest.mark.asyncio
    async def test_submit_proposal_minimal(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test submitting proposal with minimal fields."""
        payload = {
            "name": "Simple Integration",
            "description": "Just a simple integration proposal for testing.",
        }

        response = await test_client.post(
            "/api/v1/integration-proposals",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Simple Integration"
        assert data["category"] is None
        assert data["official_docs_url"] is None

    @pytest.mark.asyncio
    async def test_submit_proposal_short_description(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test that short description is rejected."""
        payload = {
            "name": "Bad Proposal",
            "description": "Too short",  # Less than 10 chars
        }

        response = await test_client.post(
            "/api/v1/integration-proposals",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_proposal_invalid_url(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test that invalid URL is rejected."""
        payload = {
            "name": "Invalid URL Proposal",
            "description": "Proposal with invalid documentation URL.",
            "official_docs_url": "not-a-valid-url",
        }

        response = await test_client.post(
            "/api/v1/integration-proposals",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_proposal_requires_auth(
        self,
        test_client: AsyncClient,
    ):
        """Test that submitting proposal requires authentication."""
        payload = {
            "name": "Unauthorized Proposal",
            "description": "Should fail because not authenticated.",
        }

        response = await test_client.post(
            "/api/v1/integration-proposals",
            json=payload,
        )

        assert response.status_code == 401


class TestGetMyProposals:
    """Tests for GET /api/v1/integration-proposals/mine"""

    @pytest.mark.asyncio
    async def test_get_my_proposals(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_proposal,
    ):
        """Test getting user's own proposals."""
        response = await test_client.get(
            "/api/v1/integration-proposals/mine",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["name"] == test_proposal.name
        assert data[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_my_proposals_empty(
        self,
        test_client: AsyncClient,
        test_admin_token,
    ):
        """Test getting empty list when no proposals."""
        response = await test_client.get(
            "/api/v1/integration-proposals/mine",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_my_proposals_requires_auth(
        self,
        test_client: AsyncClient,
    ):
        """Test that getting proposals requires authentication."""
        response = await test_client.get(
            "/api/v1/integration-proposals/mine",
        )

        assert response.status_code == 401


class TestAdminListProposals:
    """Tests for GET /api/v1/admin/integration-proposals"""

    @pytest.mark.asyncio
    async def test_admin_list_all_proposals(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_proposal,
    ):
        """Test admin can see all proposals."""
        response = await test_client.get(
            "/api/v1/admin/integration-proposals",
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        proposal = next(p for p in data if p["id"] == str(test_proposal.id))
        assert proposal["name"] == test_proposal.name
        assert "submitted_by_name" in proposal

    @pytest.mark.asyncio
    async def test_admin_list_requires_admin(
        self,
        test_client: AsyncClient,
        test_user_token,
    ):
        """Test that regular users cannot list all proposals."""
        response = await test_client.get(
            "/api/v1/admin/integration-proposals",
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 403


class TestAdminUpdateProposal:
    """Tests for PATCH /api/v1/admin/integration-proposals/{id}"""

    @pytest.mark.asyncio
    async def test_approve_proposal(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_proposal,
    ):
        """Test admin can approve a proposal."""
        payload = {
            "status": "approved",
            "admin_notes": "Great idea! Will implement soon.",
        }

        response = await test_client.patch(
            f"/api/v1/admin/integration-proposals/{test_proposal.id}",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "approved"
        assert data["admin_notes"] == "Great idea! Will implement soon."

    @pytest.mark.asyncio
    async def test_reject_proposal(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_proposal,
    ):
        """Test admin can reject a proposal."""
        payload = {
            "status": "rejected",
            "admin_notes": "Not a good fit for our platform.",
        }

        response = await test_client.patch(
            f"/api/v1/admin/integration-proposals/{test_proposal.id}",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_update_proposal_invalid_status(
        self,
        test_client: AsyncClient,
        test_admin_token,
        test_proposal,
    ):
        """Test that invalid status is rejected."""
        payload = {
            "status": "invalid_status",
        }

        response = await test_client.patch(
            f"/api/v1/admin/integration-proposals/{test_proposal.id}",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_proposal_not_found(
        self,
        test_client: AsyncClient,
        test_admin_token,
    ):
        """Test 404 for non-existent proposal."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        payload = {
            "status": "approved",
        }

        response = await test_client.patch(
            f"/api/v1/admin/integration-proposals/{fake_id}",
            json=payload,
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_proposal_requires_admin(
        self,
        test_client: AsyncClient,
        test_user_token,
        test_proposal,
    ):
        """Test that regular users cannot update proposals."""
        payload = {
            "status": "approved",
        }

        response = await test_client.patch(
            f"/api/v1/admin/integration-proposals/{test_proposal.id}",
            json=payload,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 403
