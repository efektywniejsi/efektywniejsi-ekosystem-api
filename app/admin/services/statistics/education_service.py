"""Education statistics service."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.admin.schemas.admin_statistics import (
    CertificateDetail,
    CertificatesListResponse,
    CompletionDetail,
    CompletionsListResponse,
    CourseProgressStats,
    EducationKPI,
    EducationStatisticsResponse,
)
from app.auth.models.user import User
from app.courses.models.certificate import Certificate
from app.courses.models.course import Course, Lesson, Module
from app.courses.models.enrollment import Enrollment
from app.courses.models.progress import LessonProgress


class EducationService:
    """Service for education-related statistics."""

    @staticmethod
    def get_kpis(db: Session, month_start: datetime) -> EducationKPI:
        """Get education KPIs for dashboard.

        Args:
            db: Database session.
            month_start: Start of current month.

        Returns:
            EducationKPI with enrollment, completion, and certificate counts.
        """
        total_enrollments = db.query(Enrollment).count()
        enrollments_month = (
            db.query(Enrollment).filter(Enrollment.enrolled_at >= month_start).count()
        )
        completions_month = (
            db.query(Enrollment)
            .filter(
                Enrollment.completed_at.isnot(None),
                Enrollment.completed_at >= month_start,
            )
            .count()
        )
        certificates_month = (
            db.query(Certificate).filter(Certificate.issued_at >= month_start).count()
        )

        # Average completion rate
        total_completed = db.query(Enrollment).filter(Enrollment.completed_at.isnot(None)).count()
        avg_completion = (
            round((total_completed / total_enrollments) * 100, 2) if total_enrollments > 0 else 0.0
        )

        return EducationKPI(
            total_enrollments=total_enrollments,
            enrollments_this_month=enrollments_month,
            completions_this_month=completions_month,
            certificates_this_month=certificates_month,
            average_completion_rate=avg_completion,
        )

    @staticmethod
    def get_statistics(db: Session) -> EducationStatisticsResponse:
        """Get education statistics with course details.

        Args:
            db: Database session.

        Returns:
            EducationStatisticsResponse with overall stats and per-course breakdowns.
        """
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        total_enrollments = db.query(Enrollment).count()
        active_learners = (
            db.query(func.count(func.distinct(Enrollment.user_id)))
            .filter(Enrollment.last_accessed_at >= week_ago)
            .scalar()
            or 0
        )
        total_completions = db.query(Enrollment).filter(Enrollment.completed_at.isnot(None)).count()
        total_certificates = db.query(Certificate).count()
        avg_completion_rate = (
            round((total_completions / total_enrollments) * 100, 2)
            if total_enrollments > 0
            else 0.0
        )

        # Per-course statistics — batch queries instead of N+1
        courses_data = db.query(Course).filter(Course.is_published == True).all()  # noqa: E712
        course_ids = [c.id for c in courses_data]

        # Batch: enrollment counts, active learners, completions per course
        enrollment_stats = {}
        if course_ids:
            rows = (
                db.query(
                    Enrollment.course_id,
                    func.count(Enrollment.id),
                    func.count(Enrollment.id).filter(Enrollment.last_accessed_at >= week_ago),
                    func.count(Enrollment.id).filter(Enrollment.completed_at.isnot(None)),
                )
                .filter(Enrollment.course_id.in_(course_ids))
                .group_by(Enrollment.course_id)
                .all()
            )
            enrollment_stats = {
                r[0]: {"total": r[1], "active": r[2], "completed": r[3]} for r in rows
            }

        # Batch: certificate counts per course
        cert_stats = {}
        if course_ids:
            rows = (
                db.query(Certificate.course_id, func.count(Certificate.id))
                .filter(Certificate.course_id.in_(course_ids))
                .group_by(Certificate.course_id)
                .all()
            )
            cert_stats = {r[0]: r[1] for r in rows}

        # Batch: total lesson count per course (Course -> Module -> Lesson)
        lesson_counts = {}
        if course_ids:
            rows = (
                db.query(Module.course_id, func.count(Lesson.id))
                .join(Lesson, Lesson.module_id == Module.id)
                .filter(Module.course_id.in_(course_ids))
                .group_by(Module.course_id)
                .all()
            )
            lesson_counts = {r[0]: r[1] for r in rows}

        # Batch: sum of completion_percentage per course, scoped to lessons that
        # belong to the course AND to users actually enrolled in that course.
        # Average progress treats never-started lessons as 0% (see denominator below).
        progress_sums = {}
        if course_ids:
            rows = (
                db.query(
                    Module.course_id,
                    func.sum(LessonProgress.completion_percentage),
                )
                .join(Lesson, Lesson.module_id == Module.id)
                .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
                .join(
                    Enrollment,
                    (Enrollment.user_id == LessonProgress.user_id)
                    & (Enrollment.course_id == Module.course_id),
                )
                .filter(Module.course_id.in_(course_ids))
                .group_by(Module.course_id)
                .all()
            )
            progress_sums = {r[0]: (r[1] or 0) for r in rows}

        courses = []
        for course in courses_data:
            e_stats = enrollment_stats.get(course.id, {"total": 0, "active": 0, "completed": 0})
            # Average progress = achieved percentage points / total possible points.
            # Denominator counts every enrolled user × every lesson, so lessons a user
            # never opened correctly count as 0% instead of inflating the average.
            total_lessons = lesson_counts.get(course.id, 0)
            denominator = e_stats["total"] * total_lessons
            average_progress = (
                round(progress_sums.get(course.id, 0) / denominator, 2)
                if denominator > 0
                else 0.0
            )
            courses.append(
                CourseProgressStats(
                    id=str(course.id),
                    title=course.title,
                    slug=course.slug,
                    total_enrollments=e_stats["total"],
                    active_learners=e_stats["active"],
                    completed_count=e_stats["completed"],
                    average_progress=average_progress,
                    certificates_issued=cert_stats.get(course.id, 0),
                )
            )

        return EducationStatisticsResponse(
            total_enrollments=total_enrollments,
            active_learners=active_learners,
            total_completions=total_completions,
            total_certificates=total_certificates,
            average_completion_rate=avg_completion_rate,
            courses=courses,
        )

    @staticmethod
    def get_completions(db: Session, limit: int = 50) -> CompletionsListResponse:
        """Get all course completions (most recent first).

        Args:
            db: Database session.
            limit: Maximum number of completions to return.

        Returns:
            CompletionsListResponse with total count and completion details.
        """
        total = db.query(Enrollment).filter(Enrollment.completed_at.isnot(None)).count()

        enrollments = (
            db.query(Enrollment)
            .filter(Enrollment.completed_at.isnot(None))
            .order_by(Enrollment.completed_at.desc())
            .limit(limit)
            .all()
        )

        # Batch load users and courses to avoid N+1
        user_ids = list({e.user_id for e in enrollments})
        course_ids = list({e.course_id for e in enrollments})
        users_map = (
            {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
            if user_ids
            else {}
        )
        courses_map = (
            {c.id: c for c in db.query(Course).filter(Course.id.in_(course_ids)).all()}
            if course_ids
            else {}
        )

        completions = []
        for e in enrollments:
            user = users_map.get(e.user_id)
            course = courses_map.get(e.course_id)
            completions.append(
                CompletionDetail(
                    user_email=user.email if user else "",
                    user_name=user.name if user else None,
                    course_title=course.title if course else "",
                    completed_at=e.completed_at,
                )
            )

        return CompletionsListResponse(total=total, completions=completions)

    @staticmethod
    def get_certificates(db: Session, limit: int = 50) -> CertificatesListResponse:
        """Get all issued certificates (most recent first).

        Args:
            db: Database session.
            limit: Maximum number of certificates to return.

        Returns:
            CertificatesListResponse with total count and certificate details.
        """
        total = db.query(Certificate).count()

        certs = db.query(Certificate).order_by(Certificate.issued_at.desc()).limit(limit).all()

        # Batch load users and courses to avoid N+1
        user_ids = list({c.user_id for c in certs})
        course_ids = list({c.course_id for c in certs})
        users_map = (
            {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
            if user_ids
            else {}
        )
        courses_map = (
            {co.id: co for co in db.query(Course).filter(Course.id.in_(course_ids)).all()}
            if course_ids
            else {}
        )

        certificates = []
        for c in certs:
            user = users_map.get(c.user_id)
            course = courses_map.get(c.course_id)
            certificates.append(
                CertificateDetail(
                    user_email=user.email if user else "",
                    user_name=user.name if user else None,
                    course_title=course.title if course else "",
                    certificate_code=c.certificate_code,
                    issued_at=c.issued_at,
                )
            )

        return CertificatesListResponse(total=total, certificates=certificates)
