"""
E2E tests for certificate generation and management.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_certificate_after_course_completion(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_course_with_modules,
    db_session,
):
    """Test certificate generation after completing all lessons."""
    from datetime import datetime

    from app.courses.models import Enrollment, Lesson, LessonProgress

    # Enroll user
    enrollment = Enrollment(
        user_id=test_user.id,
        course_id=test_course_with_modules.id,
        enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)
    db_session.flush()

    # Get all lessons
    lessons = (
        db_session.query(Lesson)
        .join(Lesson.module)
        .filter(Lesson.module.has(course_id=test_course_with_modules.id))
        .all()
    )

    # Mark all lessons as completed
    for lesson in lessons:
        lesson_progress = LessonProgress(
            user_id=test_user.id,
            lesson_id=lesson.id,
            watched_seconds=lesson.duration_seconds,
            last_position_seconds=lesson.duration_seconds,
            completion_percentage=100,
            is_completed=True,
            completed_at=datetime.utcnow(),
        )
        db_session.add(lesson_progress)
    db_session.flush()

    # Generate certificate
    response = await test_client.post(
        f"/api/v1/certificates/courses/{test_course_with_modules.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["course_id"] == str(test_course_with_modules.id)
    assert data["certificate_code"] is not None
    assert data["issued_at"] is not None


@pytest.mark.asyncio
async def test_cannot_generate_certificate_without_completion(
    test_client: AsyncClient,
    test_user_token,
    test_course,
    test_enrollment,
):
    """Test cannot generate certificate without completing course."""
    response = await test_client.post(
        f"/api/v1/certificates/courses/{test_course.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 400
    assert "not completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_user_certificates(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_course,
    db_session,
):
    """Test getting user's certificates."""
    from datetime import datetime

    from app.courses.models import Certificate

    # Create certificate
    certificate = Certificate(
        user_id=test_user.id,
        course_id=test_course.id,
        certificate_code="TEST-CERT-2026-001",
        issued_at=datetime.utcnow(),
    )
    db_session.add(certificate)
    db_session.flush()

    response = await test_client.get(
        "/api/v1/certificates/me",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["certificate_code"] == "TEST-CERT-2026-001"


@pytest.mark.asyncio
async def test_download_certificate(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_course,
    db_session,
):
    """Test downloading certificate PDF."""
    from datetime import datetime

    from app.courses.models import Certificate

    # Create certificate
    certificate = Certificate(
        user_id=test_user.id,
        course_id=test_course.id,
        certificate_code="TEST-CERT-2026-002",
        issued_at=datetime.utcnow(),
    )
    db_session.add(certificate)
    db_session.flush()

    response = await test_client.get(
        "/api/v1/certificates/TEST-CERT-2026-002/download",
        cookies={"access_token": test_user_token},
    )

    # Should return PDF or 200 status
    assert response.status_code in [200, 201]
    # Check Content-Type is PDF
    if response.status_code == 200:
        assert "application/pdf" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_verify_certificate_public(
    test_client: AsyncClient,
    test_user,
    test_course,
    db_session,
):
    """Test public certificate verification (no auth needed)."""
    from datetime import datetime

    from app.courses.models import Certificate

    # Create certificate
    certificate = Certificate(
        user_id=test_user.id,
        course_id=test_course.id,
        certificate_code="TEST-CERT-2026-003",
        issued_at=datetime.utcnow(),
    )
    db_session.add(certificate)
    db_session.flush()

    # Verify without authentication
    response = await test_client.get("/api/v1/certificates/TEST-CERT-2026-003/verify")

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["course_title"] == test_course.title


@pytest.mark.asyncio
async def test_verify_invalid_certificate(test_client: AsyncClient):
    """Test verifying invalid certificate code."""
    response = await test_client.get("/api/v1/certificates/INVALID-CODE/verify")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_generate_duplicate_certificate(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_course_with_modules,
    db_session,
):
    """Test cannot generate certificate twice for same course."""
    from datetime import datetime

    from app.courses.models import Certificate, Enrollment, Lesson, LessonProgress

    # Enroll and complete course
    enrollment = Enrollment(
        user_id=test_user.id,
        course_id=test_course_with_modules.id,
        enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)

    lessons = (
        db_session.query(Lesson)
        .join(Lesson.module)
        .filter(Lesson.module.has(course_id=test_course_with_modules.id))
        .all()
    )

    for lesson in lessons:
        lesson_progress = LessonProgress(
            user_id=test_user.id,
            lesson_id=lesson.id,
            watched_seconds=lesson.duration_seconds,
            last_position_seconds=lesson.duration_seconds,
            completion_percentage=100,
            is_completed=True,
            completed_at=datetime.utcnow(),
        )
        db_session.add(lesson_progress)

    # Create existing certificate
    certificate = Certificate(
        user_id=test_user.id,
        course_id=test_course_with_modules.id,
        certificate_code="EXISTING-CERT",
        issued_at=datetime.utcnow(),
    )
    db_session.add(certificate)
    db_session.flush()

    # Try to generate again
    response = await test_client.post(
        f"/api/v1/certificates/courses/{test_course_with_modules.id}",
        cookies={"access_token": test_user_token},
    )

    assert response.status_code == 400
    assert "already has a certificate" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_certificate_updates_enrollment(
    test_client: AsyncClient,
    test_user_token,
    test_user,
    test_course_with_modules,
    db_session,
):
    """Test certificate generation updates enrollment completion."""
    from datetime import datetime

    from app.courses.models import Enrollment, Lesson, LessonProgress

    # Enroll
    enrollment = Enrollment(
        user_id=test_user.id,
        course_id=test_course_with_modules.id,
        enrolled_at=datetime.utcnow(),
        completed_at=None,
        certificate_issued_at=None,
    )
    db_session.add(enrollment)

    # Complete all lessons
    lessons = (
        db_session.query(Lesson)
        .join(Lesson.module)
        .filter(Lesson.module.has(course_id=test_course_with_modules.id))
        .all()
    )

    for lesson in lessons:
        lesson_progress = LessonProgress(
            user_id=test_user.id,
            lesson_id=lesson.id,
            watched_seconds=lesson.duration_seconds,
            completion_percentage=100,
            is_completed=True,
            completed_at=datetime.utcnow(),
        )
        db_session.add(lesson_progress)
    db_session.flush()

    # Generate certificate
    await test_client.post(
        f"/api/v1/certificates/courses/{test_course_with_modules.id}",
        cookies={"access_token": test_user_token},
    )

    # Check enrollment updated
    db_session.refresh(enrollment)
    assert enrollment.completed_at is not None
    assert enrollment.certificate_issued_at is not None
