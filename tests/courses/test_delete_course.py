"""
Tests for delete course with password confirmation endpoint.
"""

from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.courses.models import Course, Lesson, Module
from app.courses.services.mux_service import get_mux_service


@pytest.fixture
def test_course_with_video_lessons(db_session: Session):
    """Create a course with modules and lessons that have Mux assets."""
    course = Course(
        slug="deletable-course",
        title="Deletable Course",
        description="A course to be deleted",
        difficulty="beginner",
        estimated_hours=5,
        is_published=True,
        category="test",
        sort_order=0,
    )
    db_session.add(course)
    db_session.flush()

    module = Module(
        course_id=course.id,
        title="Test Module",
        description="Module description",
        sort_order=0,
    )
    db_session.add(module)
    db_session.flush()

    lesson1 = Lesson(
        module_id=module.id,
        title="Lesson with video",
        description="Has Mux asset",
        mux_playback_id="playback_123",
        mux_asset_id="asset_123",
        duration_seconds=300,
        sort_order=0,
    )
    lesson2 = Lesson(
        module_id=module.id,
        title="Lesson without video",
        description="No Mux asset",
        mux_playback_id=None,
        mux_asset_id=None,
        duration_seconds=0,
        sort_order=1,
    )
    db_session.add_all([lesson1, lesson2])
    db_session.flush()

    return course


@pytest.fixture
def mock_mux_service():
    """Create a mock MuxService."""
    mock = MagicMock()
    mock.delete_asset = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_delete_course_with_correct_password(
    test_client: AsyncClient,
    test_admin_token,
    test_course_with_video_lessons,
    db_session: Session,
    test_app,
    mock_mux_service,
):
    """Test admin can delete course with correct password."""
    from app.main import app

    # Override the dependency
    app.dependency_overrides[get_mux_service] = lambda: mock_mux_service

    try:
        course_id = test_course_with_video_lessons.id

        response = await test_client.post(
            f"/api/v1/courses/{course_id}/delete-with-password",
            json={"password": "adminpass123"},
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Deletable Course" in data["message"]
        assert data["warnings"] == []

        # Verify Mux service was called to delete the asset
        mock_mux_service.delete_asset.assert_called_once_with("asset_123")

        # Verify course is deleted from database
        deleted_course = db_session.query(Course).filter(Course.id == course_id).first()
        assert deleted_course is None
    finally:
        # Clean up
        if get_mux_service in app.dependency_overrides:
            del app.dependency_overrides[get_mux_service]


@pytest.mark.asyncio
async def test_delete_course_with_wrong_password(
    test_client: AsyncClient,
    test_admin_token,
    test_course,
):
    """Test admin cannot delete course with wrong password."""
    response = await test_client.post(
        f"/api/v1/courses/{test_course.id}/delete-with-password",
        json={"password": "wrongpassword123"},
        cookies={"access_token": test_admin_token},
    )

    assert response.status_code == 403
    assert "hasło" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_course_not_found(
    test_client: AsyncClient,
    test_admin_token,
):
    """Test deleting non-existent course returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = await test_client.post(
        f"/api/v1/courses/{fake_id}/delete-with-password",
        json={"password": "adminpass123"},
        cookies={"access_token": test_admin_token},
    )

    assert response.status_code == 404
    assert "nie znalezion" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_course_non_admin_forbidden(
    test_client: AsyncClient,
    test_user_token,
    test_course,
):
    """Test non-admin user cannot delete course."""
    response = await test_client.post(
        f"/api/v1/courses/{test_course.id}/delete-with-password",
        json={"password": "testpass123"},
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_course_without_auth(
    test_client: AsyncClient,
    test_course,
):
    """Test deleting course requires authentication."""
    response = await test_client.post(
        f"/api/v1/courses/{test_course.id}/delete-with-password",
        json={"password": "somepassword123"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_course_password_too_short(
    test_client: AsyncClient,
    test_admin_token,
    test_course,
):
    """Test password validation - minimum 8 characters."""
    response = await test_client.post(
        f"/api/v1/courses/{test_course.id}/delete-with-password",
        json={"password": "short"},
        cookies={"access_token": test_admin_token},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_course_mux_failure_returns_warning(
    test_client: AsyncClient,
    test_admin_token,
    test_course_with_video_lessons,
    db_session: Session,
    test_app,
):
    """Test that Mux deletion failures are returned as warnings."""
    from app.main import app

    # Create a mock that raises an exception
    mock_service = MagicMock()
    mock_service.delete_asset.side_effect = Exception("Mux API error")

    app.dependency_overrides[get_mux_service] = lambda: mock_service

    try:
        course_id = test_course_with_video_lessons.id

        response = await test_client.post(
            f"/api/v1/courses/{course_id}/delete-with-password",
            json={"password": "adminpass123"},
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) == 1
        assert "Mux" in data["warnings"][0]
        assert "asset_123" in data["warnings"][0]

        # Course should still be deleted even if Mux fails
        deleted_course = db_session.query(Course).filter(Course.id == course_id).first()
        assert deleted_course is None
    finally:
        if get_mux_service in app.dependency_overrides:
            del app.dependency_overrides[get_mux_service]


@pytest.mark.asyncio
async def test_delete_course_cascade_deletes_modules_and_lessons(
    test_client: AsyncClient,
    test_admin_token,
    test_course_with_video_lessons,
    db_session: Session,
    test_app,
    mock_mux_service,
):
    """Test that deleting course also deletes modules and lessons (CASCADE)."""
    from app.main import app

    app.dependency_overrides[get_mux_service] = lambda: mock_mux_service

    try:
        course_id = test_course_with_video_lessons.id

        # Count before deletion
        modules_before = db_session.query(Module).filter(Module.course_id == course_id).count()
        lessons_before = (
            db_session.query(Lesson).join(Module).filter(Module.course_id == course_id).count()
        )
        assert modules_before == 1
        assert lessons_before == 2

        response = await test_client.post(
            f"/api/v1/courses/{course_id}/delete-with-password",
            json={"password": "adminpass123"},
            cookies={"access_token": test_admin_token},
        )

        assert response.status_code == 200

        # Verify cascade deletion
        modules_after = db_session.query(Module).filter(Module.course_id == course_id).count()
        lessons_after = (
            db_session.query(Lesson).join(Module).filter(Module.course_id == course_id).count()
        )
        assert modules_after == 0
        assert lessons_after == 0
    finally:
        if get_mux_service in app.dependency_overrides:
            del app.dependency_overrides[get_mux_service]
