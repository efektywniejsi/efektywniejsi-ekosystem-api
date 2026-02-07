"""
E2E tests for course enrollment flow.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_enroll_in_course(test_client: AsyncClient, test_user_token, test_course):
    """Test user can enroll in a course."""
    # Enroll in course
    response = await test_client.post(
        f"/api/v1/courses/{test_course.id}/enroll",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["course_id"] == str(test_course.id)
    assert data["enrolled_at"] is not None


@pytest.mark.asyncio
async def test_cannot_enroll_twice(
    test_client: AsyncClient, test_user_token, test_course, test_enrollment
):
    """Test user cannot enroll twice in same course."""
    response = await test_client.post(
        f"/api/v1/courses/{test_course.id}/enroll",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 409
    assert "already enrolled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_my_enrollments(test_client: AsyncClient, test_user_token, test_enrollment):
    """Test getting user's enrollments."""
    response = await test_client.get(
        "/api/v1/enrollments/me",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["course"]["slug"] == "test-course"


@pytest.mark.asyncio
async def test_enroll_without_auth(test_client: AsyncClient, test_course):
    """Test enrollment requires authentication."""
    response = await test_client.post(f"/api/v1/courses/{test_course.id}/enroll")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_enroll_nonexistent_course(test_client: AsyncClient, test_user_token):
    """Test enrolling in non-existent course."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await test_client.post(
        f"/api/v1/courses/{fake_id}/enroll",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enrollment_grants_access_to_lessons(
    test_client: AsyncClient,
    test_user_token,
    test_course,
    test_lesson,
    test_enrollment,
):
    """Test enrollment grants access to course lessons."""
    response = await test_client.get(
        f"/api/v1/lessons/{test_lesson.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_lesson.id)
    assert data["title"] == test_lesson.title


@pytest.mark.asyncio
async def test_no_enrollment_no_access(test_client: AsyncClient, test_user_token, test_lesson):
    """Test user cannot access lessons without enrollment."""
    response = await test_client.get(
        f"/api/v1/lessons/{test_lesson.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 403
    assert "enrolled" in response.json()["detail"].lower()
