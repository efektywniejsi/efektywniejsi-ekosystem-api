"""Unit tests for EducationService.get_statistics average-progress computation.

These tests pin the corrected behaviour of the per-course "śr. postęp" metric.
The previous implementation joined Enrollment to LessonProgress on user_id only,
which (1) leaked a user's progress from one course into every other course they
were enrolled in, and (2) averaged only over lessons that had been opened, so
never-started lessons silently inflated the result.

The fix scopes progress to the course's own lessons (Course -> Module -> Lesson)
and divides by enrollments x total_lessons, so never-started lessons count as 0%.
"""

from sqlalchemy.orm import Session

from app.admin.services.statistics.education_service import EducationService
from app.courses.models.course import Course, Lesson, Module
from app.courses.models.enrollment import Enrollment
from app.courses.models.progress import LessonProgress
from tests.utils.factories import create_user_factory


def _course(db: Session, slug: str, title: str) -> Course:
    course = Course(
        slug=slug,
        title=title,
        description="x",
        estimated_hours=1,
        is_published=True,
        is_featured=False,
        category="test",
        sort_order=0,
    )
    db.add(course)
    db.flush()
    return course


def _two_lessons(db: Session, course: Course) -> tuple[Lesson, Lesson]:
    module = Module(course_id=course.id, title="M", description="", sort_order=0)
    db.add(module)
    db.flush()
    l1 = Lesson(module_id=module.id, title="L1", duration_seconds=10, sort_order=0)
    l2 = Lesson(module_id=module.id, title="L2", duration_seconds=10, sort_order=1)
    db.add_all([l1, l2])
    db.flush()
    return l1, l2


def _enroll(db: Session, user_id, course_id) -> None:
    db.add(Enrollment(user_id=user_id, course_id=course_id))
    db.flush()


def _progress(db: Session, user_id, lesson_id, pct: int) -> None:
    db.add(LessonProgress(user_id=user_id, lesson_id=lesson_id, completion_percentage=pct))
    db.flush()


def test_average_progress_no_cross_course_leak_and_counts_unstarted_as_zero(
    db_session: Session,
):
    """Average progress is course-scoped and treats never-started lessons as 0%."""
    course_a = _course(db_session, "course-a", "Course A")
    course_b = _course(db_session, "course-b", "Course B")
    a1, a2 = _two_lessons(db_session, course_a)
    b1, _b2 = _two_lessons(db_session, course_b)

    user1 = create_user_factory(db_session, email="u1@example.com")
    user2 = create_user_factory(db_session, email="u2@example.com")

    # user1 is in BOTH courses — the old query would leak B's progress into A.
    _enroll(db_session, user1.id, course_a.id)
    _enroll(db_session, user1.id, course_b.id)
    # user2 is in course A only.
    _enroll(db_session, user2.id, course_a.id)

    # Course A progress: user1 -> a1=100 (a2 never started), user2 -> a1=80, a2=60
    _progress(db_session, user1.id, a1.id, 100)
    _progress(db_session, user2.id, a1.id, 80)
    _progress(db_session, user2.id, a2.id, 60)
    # Course B progress: user1 -> b1=50 (b2 never started)
    _progress(db_session, user1.id, b1.id, 50)

    result = EducationService.get_statistics(db_session)
    by_slug = {c.slug: c for c in result.courses}

    # Course A: sum = 100 + 80 + 60 = 240; denom = 2 enrollments x 2 lessons = 4 -> 60.0
    # (user1's a2 never-started counts as 0; user1's course-B 50 does NOT leak in)
    assert by_slug["course-a"].average_progress == 60.0
    # Course B: sum = 50; denom = 1 enrollment x 2 lessons = 2 -> 25.0
    assert by_slug["course-b"].average_progress == 25.0

    # Sanity: nobody completed an enrollment, so completed/certificates stay 0.
    assert by_slug["course-a"].completed_count == 0
    assert by_slug["course-b"].completed_count == 0


def test_average_progress_zero_when_no_lessons_or_no_enrollments(db_session: Session):
    """Empty/edge courses must not divide by zero — they report 0.0."""
    empty_course = _course(db_session, "empty-course", "Empty Course")
    _two_lessons(db_session, empty_course)  # has lessons but zero enrollments

    result = EducationService.get_statistics(db_session)
    by_slug = {c.slug: c for c in result.courses}

    assert by_slug["empty-course"].average_progress == 0.0
    assert by_slug["empty-course"].total_enrollments == 0
