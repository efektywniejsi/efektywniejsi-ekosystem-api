"""
E2E tests for lesson progress tracking.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_lesson_progress(
    test_client: AsyncClient,
    test_user_token,
    test_lesson,
    test_enrollment,
):
    """Test updating lesson progress."""
    progress_data = {
        "watched_seconds": 120,
        "last_position_seconds": 120,
        "completion_percentage": 40,
    }

    response = await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json=progress_data,
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["watched_seconds"] == 120
    assert data["completion_percentage"] == 40
    assert data["is_completed"] is False


@pytest.mark.asyncio
async def test_progress_auto_completes_at_95_percent(
    test_client: AsyncClient,
    test_user_token,
    test_lesson,
    test_enrollment,
):
    """Test lesson auto-completes at 95% completion."""
    progress_data = {
        "watched_seconds": 285,
        "last_position_seconds": 285,
        "completion_percentage": 95,
    }

    response = await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json=progress_data,
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is True
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_lesson_progress(
    test_client: AsyncClient,
    test_user_token,
    test_lesson,
    test_enrollment,
):
    """Test getting lesson progress."""
    # First update progress
    progress_data = {
        "watched_seconds": 60,
        "last_position_seconds": 60,
        "completion_percentage": 20,
    }

    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json=progress_data,
        cookies={"access_token": test_user_token},
    )

    # Get progress
    response = await test_client.get(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["watched_seconds"] == 60
    assert data["completion_percentage"] == 20


@pytest.mark.asyncio
async def test_mark_lesson_complete(
    test_client: AsyncClient,
    test_user_token,
    test_lesson,
    test_enrollment,
):
    """Test manually marking lesson as complete."""
    # First watch 95%+
    progress_data = {
        "watched_seconds": 290,
        "last_position_seconds": 290,
        "completion_percentage": 96,
    }

    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json=progress_data,
        cookies={"access_token": test_user_token},
    )

    # Mark complete
    response = await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}/complete",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is True
    assert data["completion_percentage"] == 100


@pytest.mark.asyncio
async def test_cannot_mark_complete_without_95_percent(
    test_client: AsyncClient,
    test_user_token,
    test_lesson,
    test_enrollment,
):
    """Test cannot mark complete without watching 95%."""
    # Watch only 50%
    progress_data = {
        "watched_seconds": 150,
        "last_position_seconds": 150,
        "completion_percentage": 50,
    }

    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json=progress_data,
        cookies={"access_token": test_user_token},
    )

    # Try to mark complete
    response = await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}/complete",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 400
    assert "95%" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_course_progress(
    test_client: AsyncClient,
    test_user_token,
    test_course_with_modules,
    db_session,
):
    """Test getting overall course progress."""
    from datetime import datetime

    from app.courses.models import Enrollment

    # Enroll user
    enrollment = Enrollment(
        user_id=test_user_token,  # This should be test_user.id
        course_id=test_course_with_modules.id,
        enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)
    db_session.flush()

    response = await test_client.get(
        f"/api/v1/progress/courses/{test_course_with_modules.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["course_id"] == str(test_course_with_modules.id)
    assert "total_lessons" in data
    assert "completed_lessons" in data
    assert "completion_percentage" in data


@pytest.mark.asyncio
async def test_progress_increments_watched_seconds(
    test_client: AsyncClient,
    test_user_token,
    test_lesson,
    test_enrollment,
):
    """Test watched seconds increment correctly."""
    # First update: 60s
    await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 60,
            "last_position_seconds": 60,
            "completion_percentage": 20,
        },
        cookies={"access_token": test_user_token},
    )

    # Second update: +30s more (total 90s)
    response = await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 90,
            "last_position_seconds": 90,
            "completion_percentage": 30,
        },
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["watched_seconds"] == 90


@pytest.mark.asyncio
async def test_progress_without_enrollment_fails(
    test_client: AsyncClient, test_user_token, test_lesson
):
    """Test cannot update progress without enrollment."""
    response = await test_client.post(
        f"/api/v1/progress/lessons/{test_lesson.id}",
        json={
            "watched_seconds": 60,
            "last_position_seconds": 60,
            "completion_percentage": 20,
        },
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 403
