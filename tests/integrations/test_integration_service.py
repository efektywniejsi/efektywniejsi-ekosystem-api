"""
Unit tests for IntegrationService.
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.integrations.models import Integration, LessonIntegration
from app.integrations.schemas import IntegrationCreate, IntegrationUpdate
from app.integrations.services import IntegrationService
from tests.integrations.conftest import (
    create_course_with_lesson,
    create_integration,
    create_integration_proposal,
    create_lesson_integration,
)


class TestGetPublishedIntegrations:
    """Tests for get_published_integrations method."""

    def test_returns_only_published(self, db_session: Session):
        """Test that only published integrations are returned."""
        published = create_integration(db_session, slug="published", is_published=True)
        unpublished = create_integration(db_session, slug="unpublished", is_published=False)

        service = IntegrationService(db_session)
        result = service.get_published_integrations()

        slugs = [i.slug for i in result]
        assert published.slug in slugs
        assert unpublished.slug not in slugs

    def test_filters_by_category(self, db_session: Session):
        """Test category filtering."""
        create_integration(db_session, slug="ai-int", category="AI")
        create_integration(db_session, slug="crm-int", category="CRM")

        service = IntegrationService(db_session)
        result = service.get_published_integrations(category="AI")

        assert len(result) == 1
        assert result[0].slug == "ai-int"

    def test_searches_name_and_description(self, db_session: Session):
        """Test search functionality."""
        create_integration(db_session, slug="openai", name="OpenAI", description="AI models")
        create_integration(db_session, slug="slack", name="Slack", description="Messaging platform")

        service = IntegrationService(db_session)

        # Search by name
        result = service.get_published_integrations(search="open")
        assert len(result) == 1
        assert result[0].slug == "openai"

        # Search by description
        result = service.get_published_integrations(search="messaging")
        assert len(result) == 1
        assert result[0].slug == "slack"


class TestGetIntegrationBySlug:
    """Tests for get_integration_by_slug method."""

    def test_returns_published_integration(self, db_session: Session):
        """Test getting a published integration."""
        create_integration(db_session, slug="test-slug")

        service = IntegrationService(db_session)
        result = service.get_integration_by_slug("test-slug")

        assert result.slug == "test-slug"
        assert result.auth_guide is not None

    def test_raises_404_for_unpublished(self, db_session: Session):
        """Test that unpublished integration raises 404."""
        create_integration(db_session, slug="unpublished", is_published=False)

        service = IntegrationService(db_session)

        with pytest.raises(HTTPException) as exc:
            service.get_integration_by_slug("unpublished")

        assert exc.value.status_code == 404

    def test_raises_404_for_nonexistent(self, db_session: Session):
        """Test that non-existent slug raises 404."""
        service = IntegrationService(db_session)

        with pytest.raises(HTTPException) as exc:
            service.get_integration_by_slug("does-not-exist")

        assert exc.value.status_code == 404

    def test_includes_unpublished_when_requested(self, db_session: Session):
        """Test include_unpublished parameter."""
        integration = create_integration(db_session, slug="unpublished", is_published=False)

        service = IntegrationService(db_session)
        result = service.get_integration_by_slug("unpublished", include_unpublished=True)

        assert result.slug == integration.slug


class TestCreateIntegration:
    """Tests for create_integration method."""

    def test_creates_integration(self, db_session: Session, test_admin):
        """Test creating a new integration."""
        service = IntegrationService(db_session)

        data = IntegrationCreate(
            slug="new-integration",
            name="New Integration",
            icon="Star",
            category="AI",
            description="A new integration.",
            integration_types=["API", "MCP"],
        )

        result = service.create_integration(data, test_admin)

        assert result.slug == "new-integration"
        assert result.name == "New Integration"
        assert "API" in result.integration_types
        assert "MCP" in result.integration_types

    def test_raises_for_duplicate_slug(self, db_session: Session, test_admin):
        """Test that duplicate slug raises error."""
        create_integration(db_session, slug="existing-slug")

        service = IntegrationService(db_session)

        data = IntegrationCreate(
            slug="existing-slug",
            name="Duplicate",
            icon="Star",
            category="AI",
            description="Duplicate slug test.",
            integration_types=[],
        )

        with pytest.raises(HTTPException) as exc:
            service.create_integration(data, test_admin)

        assert exc.value.status_code == 400


class TestUpdateIntegration:
    """Tests for update_integration method."""

    def test_updates_fields(self, db_session: Session):
        """Test updating integration fields."""
        integration = create_integration(db_session, slug="to-update", name="Original")

        service = IntegrationService(db_session)

        data = IntegrationUpdate(
            name="Updated Name",
            description="Updated description",
        )

        result = service.update_integration(integration.id, data)

        assert result.name == "Updated Name"
        assert result.description == "Updated description"
        assert result.slug == "to-update"  # Unchanged

    def test_updates_integration_types(self, db_session: Session):
        """Test updating integration types."""
        integration = create_integration(db_session, slug="type-update", integration_types=["API"])

        service = IntegrationService(db_session)

        data = IntegrationUpdate(integration_types=["OAuth 2.0", "MCP"])

        result = service.update_integration(integration.id, data)

        assert "OAuth 2.0" in result.integration_types
        assert "MCP" in result.integration_types
        assert "API" not in result.integration_types

    def test_raises_404_for_nonexistent(self, db_session: Session):
        """Test that updating non-existent integration raises 404."""
        service = IntegrationService(db_session)
        fake_id = uuid.uuid4()

        data = IntegrationUpdate(name="Updated")

        with pytest.raises(HTTPException) as exc:
            service.update_integration(fake_id, data)

        assert exc.value.status_code == 404


class TestDeleteIntegration:
    """Tests for delete_integration method."""

    def test_deletes_integration(self, db_session: Session):
        """Test deleting an integration."""
        integration = create_integration(db_session, slug="to-delete")
        integration_id = integration.id

        service = IntegrationService(db_session)
        service.delete_integration(integration_id)

        # Verify deletion
        deleted = db_session.query(Integration).filter(Integration.id == integration_id).first()
        assert deleted is None

    def test_cascades_to_lesson_integrations(self, db_session: Session):
        """Test that deleting integration cascades to lesson links."""
        integration = create_integration(db_session, slug="cascading")
        _, _, lesson = create_course_with_lesson(db_session, slug="cascade-course")
        lesson_int = create_lesson_integration(
            db_session, lesson_id=lesson.id, integration_id=integration.id
        )
        lesson_int_id = lesson_int.id

        service = IntegrationService(db_session)
        service.delete_integration(integration.id)

        # Verify cascade
        link = (
            db_session.query(LessonIntegration)
            .filter(LessonIntegration.id == lesson_int_id)
            .first()
        )
        assert link is None


class TestUsageCounts:
    """Tests for usage count functionality."""

    def test_usage_count_in_list(self, db_session: Session):
        """Test that usage counts are correct in list response."""
        integration = create_integration(db_session, slug="used-integration")
        _, _, lesson1 = create_course_with_lesson(db_session, slug="course-1")
        _, _, lesson2 = create_course_with_lesson(db_session, slug="course-2")

        create_lesson_integration(db_session, lesson_id=lesson1.id, integration_id=integration.id)
        create_lesson_integration(db_session, lesson_id=lesson2.id, integration_id=integration.id)

        service = IntegrationService(db_session)
        result = service.get_published_integrations()

        int_response = next(i for i in result if i.slug == integration.slug)
        assert int_response.usage_count == 2

    def test_usage_count_zero_when_unused(self, db_session: Session):
        """Test that unused integration has count of 0."""
        integration = create_integration(db_session, slug="unused-integration")

        service = IntegrationService(db_session)
        result = service.get_published_integrations()

        int_response = next(i for i in result if i.slug == integration.slug)
        assert int_response.usage_count == 0


class TestProposals:
    """Tests for proposal methods."""

    def test_create_proposal(self, db_session: Session, test_user):
        """Test creating a proposal."""
        from app.integrations.schemas import ProposalCreate

        service = IntegrationService(db_session)

        data = ProposalCreate(
            name="New Tool",
            category="Tools",
            description="A proposal for a new tool integration.",
        )

        result = service.create_proposal(data, test_user)

        assert result.name == "New Tool"
        assert result.status == "pending"
        assert result.submitted_by_id == test_user.id

    def test_get_user_proposals(self, db_session: Session, test_user):
        """Test getting user's proposals."""
        create_integration_proposal(db_session, submitted_by_id=test_user.id, name="Proposal 1")
        create_integration_proposal(db_session, submitted_by_id=test_user.id, name="Proposal 2")

        service = IntegrationService(db_session)
        result = service.get_user_proposals(test_user)

        assert len(result) == 2

    def test_update_proposal_status(self, db_session: Session, test_user):
        """Test updating proposal status."""
        from app.integrations.schemas import ProposalUpdate

        proposal = create_integration_proposal(db_session, submitted_by_id=test_user.id)

        service = IntegrationService(db_session)

        data = ProposalUpdate(status="approved", admin_notes="Looks good!")

        result = service.update_proposal(proposal.id, data)

        assert result.status == "approved"
        assert result.admin_notes == "Looks good!"
