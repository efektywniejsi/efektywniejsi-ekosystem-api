"""
Fixtures for integrations tests.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.courses.models.course import Course, Lesson, Module
from app.integrations.models import (
    Integration,
    IntegrationProposal,
    IntegrationType,
    LessonIntegration,
)


def create_integration(
    db_session: Session,
    slug: str = "test-integration",
    name: str = "Test Integration",
    icon: str = "TestIcon",
    category: str = "AI",
    description: str = "Test integration description",
    auth_guide: str | None = "# How to get API key\n1. Go to website\n2. Create account",
    official_docs_url: str | None = "https://example.com/docs",
    video_tutorial_url: str | None = "https://youtube.com/watch?v=123",
    is_published: bool = True,
    sort_order: int = 0,
    integration_types: list[str] | None = None,
    created_by_id: uuid.UUID | None = None,
) -> Integration:
    """Factory to create an integration for testing."""
    integration = Integration(
        id=uuid.uuid4(),
        slug=slug,
        name=name,
        icon=icon,
        category=category,
        description=description,
        auth_guide=auth_guide,
        official_docs_url=official_docs_url,
        video_tutorial_url=video_tutorial_url,
        is_published=is_published,
        sort_order=sort_order,
        created_by_id=created_by_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(integration)
    db_session.flush()

    # Add integration types
    if integration_types:
        for type_name in integration_types:
            db_session.add(
                IntegrationType(
                    id=uuid.uuid4(),
                    integration_id=integration.id,
                    type_name=type_name,
                )
            )

    db_session.commit()
    db_session.refresh(integration)
    return integration


def create_integration_proposal(
    db_session: Session,
    submitted_by_id: uuid.UUID,
    name: str = "New Integration Proposal",
    category: str | None = "CRM",
    description: str = "This is a proposal for a new integration",
    official_docs_url: str | None = "https://example.com",
    status: str = "pending",
    admin_notes: str | None = None,
) -> IntegrationProposal:
    """Factory to create an integration proposal for testing."""
    proposal = IntegrationProposal(
        id=uuid.uuid4(),
        name=name,
        category=category,
        description=description,
        official_docs_url=official_docs_url,
        submitted_by_id=submitted_by_id,
        status=status,
        admin_notes=admin_notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(proposal)
    db_session.commit()
    db_session.refresh(proposal)
    return proposal


def create_course_with_lesson(
    db_session: Session,
    slug: str = "test-course",
    title: str = "Test Course",
) -> tuple[Course, Module, Lesson]:
    """Factory to create a course with a module and lesson for testing."""
    course = Course(
        id=uuid.uuid4(),
        slug=slug,
        title=title,
        description="Test course description",
        is_published=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(course)
    db_session.flush()

    module = Module(
        id=uuid.uuid4(),
        course_id=course.id,
        title="Test Module",
        sort_order=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(module)
    db_session.flush()

    lesson = Lesson(
        id=uuid.uuid4(),
        module_id=module.id,
        title="Test Lesson",
        sort_order=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(lesson)
    db_session.commit()

    db_session.refresh(course)
    db_session.refresh(module)
    db_session.refresh(lesson)

    return course, module, lesson


def create_lesson_integration(
    db_session: Session,
    lesson_id: uuid.UUID,
    integration_id: uuid.UUID,
    context_note: str | None = "Use this integration for API calls",
    sort_order: int = 0,
) -> LessonIntegration:
    """Factory to create a lesson-integration link for testing."""
    lesson_integration = LessonIntegration(
        id=uuid.uuid4(),
        lesson_id=lesson_id,
        integration_id=integration_id,
        context_note=context_note,
        sort_order=sort_order,
        created_at=datetime.utcnow(),
    )
    db_session.add(lesson_integration)
    db_session.commit()
    db_session.refresh(lesson_integration)
    return lesson_integration


# ─────────────────────────────────────────────────────────────
# Pytest Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def test_integration(db_session):
    """Create a published test integration."""
    return create_integration(
        db_session,
        slug="openai",
        name="OpenAI",
        icon="Brain",
        category="AI",
        description="API for GPT-4, GPT-3.5, DALL-E and Whisper models.",
        integration_types=["API", "MCP"],
    )


@pytest.fixture
def test_integration_unpublished(db_session):
    """Create an unpublished test integration."""
    return create_integration(
        db_session,
        slug="internal-tool",
        name="Internal Tool",
        icon="Lock",
        category="Tools",
        description="Internal tool not yet ready for public.",
        is_published=False,
        integration_types=["API"],
    )


@pytest.fixture
def test_integrations_list(db_session):
    """Create multiple integrations for list testing."""
    integrations = [
        create_integration(
            db_session,
            slug="hubspot",
            name="HubSpot",
            icon="Database",
            category="CRM",
            description="CRM with API for contacts, companies, deals and tickets.",
            integration_types=["OAuth 2.0", "API", "MCP"],
        ),
        create_integration(
            db_session,
            slug="slack",
            name="Slack",
            icon="MessageSquare",
            category="Communication",
            description="API for messages, channels and bots.",
            integration_types=["OAuth 2.0", "API"],
        ),
        create_integration(
            db_session,
            slug="stripe",
            name="Stripe",
            icon="CreditCard",
            category="Payments",
            description="Payment API for subscriptions and invoices.",
            integration_types=["API"],
        ),
    ]
    return integrations


@pytest.fixture
def test_proposal(db_session, test_user):
    """Create a test proposal."""
    return create_integration_proposal(
        db_session,
        submitted_by_id=test_user.id,
        name="Notion Integration",
        category="Productivity",
        description="Add support for Notion API to sync notes and databases.",
    )


@pytest.fixture
def test_course_with_lesson(db_session):
    """Create a course with lesson for testing lesson integrations."""
    return create_course_with_lesson(db_session)


@pytest.fixture
def test_lesson_integration(db_session, test_integration, test_course_with_lesson):
    """Create a lesson-integration link."""
    _, _, lesson = test_course_with_lesson
    return create_lesson_integration(
        db_session,
        lesson_id=lesson.id,
        integration_id=test_integration.id,
    )
