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
from app.courses.models.course import Course
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

        # Per-course statistics
        courses_data = db.query(Course).filter(Course.is_published == True).all()  # noqa: E712

        courses = []
        for course in courses_data:
            enrollments = db.query(Enrollment).filter(Enrollment.course_id == course.id).count()
            active = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course.id,
                    Enrollment.last_accessed_at >= week_ago,
                )
                .count()
            )
            completed = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course.id,
                    Enrollment.completed_at.isnot(None),
                )
                .count()
            )
            certs = db.query(Certificate).filter(Certificate.course_id == course.id).count()

            # Calculate average progress
            progress_data = (
                db.query(func.avg(LessonProgress.completion_percentage))
                .join(
                    Enrollment,
                    (Enrollment.user_id == LessonProgress.user_id)
                    & (Enrollment.course_id == course.id),
                )
                .scalar()
            )
            avg_progress = round(progress_data or 0, 2)

            courses.append(
                CourseProgressStats(
                    id=str(course.id),
                    title=course.title,
                    slug=course.slug,
                    total_enrollments=enrollments,
                    active_learners=active,
                    completed_count=completed,
                    average_progress=avg_progress,
                    certificates_issued=certs,
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

        completions = []
        for e in enrollments:
            user = db.query(User).filter(User.id == e.user_id).first()
            course = db.query(Course).filter(Course.id == e.course_id).first()
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

        certificates = []
        for c in certs:
            user = db.query(User).filter(User.id == c.user_id).first()
            course = db.query(Course).filter(Course.id == c.course_id).first()
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
