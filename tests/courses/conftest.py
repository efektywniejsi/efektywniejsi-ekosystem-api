"""
Test fixtures for courses tests.
"""

import pytest
from sqlalchemy.orm import Session

from app.courses.models import (
    Achievement,
    Course,
    Enrollment,
    Lesson,
    Module,
)


@pytest.fixture
def test_course(db_session: Session):
    """Create a test course."""
    course = Course(
        slug="test-course",
        title="Test Course",
        description="A test course for E2E tests",
        difficulty="beginner",
        estimated_hours=5,
        is_published=True,
        is_featured=False,
        category="test",
        sort_order=0,
    )
    db_session.add(course)
    db_session.flush()
    return course


@pytest.fixture
def test_module(db_session: Session, test_course):
    """Create a test module."""
    module = Module(
        course_id=test_course.id,
        title="Test Module",
        description="A test module",
        sort_order=0,
    )
    db_session.add(module)
    db_session.flush()
    return module


@pytest.fixture
def test_lesson(db_session: Session, test_module):
    """Create a test lesson."""
    lesson = Lesson(
        module_id=test_module.id,
        title="Test Lesson",
        description="A test lesson",
        mux_playback_id="test_mux_id_123",
        mux_asset_id="test_asset_123",
        duration_seconds=300,
        is_preview=False,
        sort_order=0,
    )
    db_session.add(lesson)
    db_session.flush()
    return lesson


@pytest.fixture
def test_preview_lesson(db_session: Session, test_module):
    """Create a preview lesson."""
    lesson = Lesson(
        module_id=test_module.id,
        title="Preview Lesson",
        description="A preview lesson",
        mux_playback_id="preview_mux_id_456",
        mux_asset_id="preview_asset_456",
        duration_seconds=180,
        is_preview=True,
        sort_order=1,
    )
    db_session.add(lesson)
    db_session.flush()
    return lesson


@pytest.fixture
def test_achievement(db_session: Session):
    """Create a test achievement."""
    achievement = Achievement(
        code="test_achievement",
        title="Test Achievement",
        description="A test achievement",
        icon="star",
        points_reward=100,
        category="test",
        is_active=True,
    )
    db_session.add(achievement)
    db_session.flush()
    return achievement


@pytest.fixture
def test_enrollment(db_session: Session, test_user, test_course):
    """Create a test enrollment."""
    from datetime import datetime

    enrollment = Enrollment(
        user_id=test_user.id,
        course_id=test_course.id,
        enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)
    db_session.flush()
    return enrollment


@pytest.fixture
def test_course_with_modules(db_session: Session):
    """Create a complete course with multiple modules and lessons."""
    course = Course(
        slug="complete-test-course",
        title="Complete Test Course",
        description="A complete test course with multiple modules",
        difficulty="intermediate",
        estimated_hours=10,
        is_published=True,
        is_featured=True,
        category="test",
        sort_order=0,
    )
    db_session.add(course)
    db_session.flush()

    # Module 1
    module1 = Module(
        course_id=course.id,
        title="Module 1",
        description="First module",
        sort_order=0,
    )
    db_session.add(module1)
    db_session.flush()

    # Lessons for Module 1
    lesson1_1 = Lesson(
        module_id=module1.id,
        title="Lesson 1.1",
        description="First lesson",
        mux_playback_id="mux_1_1",
        duration_seconds=600,
        is_preview=True,
        sort_order=0,
    )
    lesson1_2 = Lesson(
        module_id=module1.id,
        title="Lesson 1.2",
        description="Second lesson",
        mux_playback_id="mux_1_2",
        duration_seconds=900,
        is_preview=False,
        sort_order=1,
    )
    db_session.add_all([lesson1_1, lesson1_2])
    db_session.flush()

    # Module 2
    module2 = Module(
        course_id=course.id,
        title="Module 2",
        description="Second module",
        sort_order=1,
    )
    db_session.add(module2)
    db_session.flush()

    # Lessons for Module 2
    lesson2_1 = Lesson(
        module_id=module2.id,
        title="Lesson 2.1",
        description="Third lesson",
        mux_playback_id="mux_2_1",
        duration_seconds=1200,
        is_preview=False,
        sort_order=0,
    )
    db_session.add(lesson2_1)
    db_session.flush()

    return course
