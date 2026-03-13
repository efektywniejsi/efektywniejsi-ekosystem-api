import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.auth.models.user_daily_activity import UserDailyActivity
from app.auth.schemas.user import (
    EnrollmentDetail,
    ThreadSummary,
    UserDetailResponse,
    UserListResponse,
    UserResponse,
    UserStats,
    UserWithStats,
)
from app.auth.services.email_service import build_admin_welcome_email, get_email_service
from app.community.models.reply import ThreadReply
from app.community.models.thread import CommunityThread
from app.core.security import generate_reset_token
from app.courses.models.certificate import Certificate
from app.courses.models.course import Course
from app.courses.models.enrollment import Enrollment
from app.courses.models.gamification import UserPoints, UserStreak
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import (
    ImplementationPackageEnrollment,
)
from app.messaging.models.conversation_participant import ConversationParticipant
from app.packages.models.bundle import BundleCourseItem, BundleImplementationPackageItem
from app.packages.models.enrollment import PackageEnrollment
from app.packages.models.package import Package

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1)
    role: Literal["paid", "admin"] = "paid"
    send_welcome_email: bool = True
    package_ids: list[uuid.UUID] = []
    course_ids: list[uuid.UUID] = []


class UpdateUserRequest(BaseModel):
    name: str | None = None
    role: Literal["paid", "admin"] | None = None
    is_active: bool | None = None


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email jest już zarejestrowany",
        )

    raw_token, hashed_token, expiry = generate_reset_token()

    new_user = User(
        id=uuid.uuid4(),
        email=request.email,
        name=request.name,
        hashed_password="!",
        role=request.role,
        is_active=True,
        password_reset_token=hashed_token,
        password_reset_token_expires=expiry,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(new_user)
    db.flush()

    _create_admin_enrollments(db, new_user.id, request.package_ids, request.course_ids)

    db.commit()
    db.refresh(new_user)

    if request.send_welcome_email:
        try:
            email_service = get_email_service()
            email_message = build_admin_welcome_email(
                name=str(new_user.name),
                email=str(new_user.email),
                token=raw_token,
            )
            await email_service.send_email(email_message)
        except Exception:
            logger.exception("Nie udało się wysłać emaila powitalnego do %s", new_user.email)

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat() if new_user.created_at else None,
    )


def _create_admin_enrollments(
    db: Session,
    user_id: uuid.UUID,
    package_ids: list[uuid.UUID],
    course_ids: list[uuid.UUID],
) -> None:
    """Create enrollments from admin-provided package and course IDs.

    Handles bundle expansion: child packages, courses, and implementation packages.
    Silently skips duplicates (matching OrderService behavior).
    """
    for pkg_id in package_ids:
        package = db.query(Package).filter(Package.id == pkg_id).first()
        if not package:
            continue

        if package.is_bundle:
            # 1. Enroll in child packages
            for bundle_item in package.bundle_items:
                _create_package_enrollment(db, user_id, bundle_item.child_package_id)

            # 2. Enroll in bundle courses
            course_items = (
                db.query(BundleCourseItem).filter(BundleCourseItem.bundle_id == package.id).all()
            )
            for course_item in course_items:
                existing = (
                    db.query(Enrollment)
                    .filter(
                        Enrollment.user_id == user_id,
                        Enrollment.course_id == course_item.course_id,
                    )
                    .first()
                )
                if not existing:
                    expires_at = None
                    if course_item.access_duration_days is not None:
                        expires_at = datetime.now(UTC) + timedelta(
                            days=course_item.access_duration_days
                        )
                    db.add(
                        Enrollment(
                            user_id=user_id,
                            course_id=course_item.course_id,
                            expires_at=expires_at,
                        )
                    )

            # 3. Enroll in bundle implementation packages
            impl_items = (
                db.query(BundleImplementationPackageItem)
                .filter(BundleImplementationPackageItem.bundle_id == package.id)
                .all()
            )
            for impl_item in impl_items:
                _create_impl_enrollment(
                    db,
                    user_id,
                    impl_item.implementation_package_id,
                    access_duration_days=impl_item.access_duration_days,
                )
        else:
            _create_package_enrollment(db, user_id, package.id)

    # Direct course enrollments
    for cid in course_ids:
        course = db.query(Course).filter(Course.id == cid).first()
        if not course:
            continue
        existing = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == cid)
            .first()
        )
        if not existing:
            db.add(Enrollment(user_id=user_id, course_id=cid))


def _create_package_enrollment(db: Session, user_id: uuid.UUID, package_id: uuid.UUID) -> None:
    """Create a PackageEnrollment, skipping if duplicate."""
    existing = (
        db.query(PackageEnrollment)
        .filter(
            PackageEnrollment.user_id == user_id,
            PackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if not existing:
        db.add(
            PackageEnrollment(
                id=uuid.uuid4(),
                user_id=user_id,
                package_id=package_id,
                order_id=None,
                enrolled_at=datetime.now(UTC),
            )
        )


def _create_impl_enrollment(
    db: Session,
    user_id: uuid.UUID,
    implementation_package_id: uuid.UUID,
    access_duration_days: int | None = None,
) -> None:
    """Create an ImplementationPackageEnrollment, skipping if duplicate."""
    existing = (
        db.query(ImplementationPackageEnrollment)
        .filter(
            ImplementationPackageEnrollment.user_id == user_id,
            ImplementationPackageEnrollment.package_id == implementation_package_id,
        )
        .first()
    )
    if not existing:
        expires_at = None
        if access_duration_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=access_duration_days)
        db.add(
            ImplementationPackageEnrollment(
                id=uuid.uuid4(),
                user_id=user_id,
                package_id=implementation_package_id,
                order_id=None,
                enrolled_at=datetime.now(UTC),
                expires_at=expires_at,
            )
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    role: Literal["paid", "admin"] | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserListResponse:
    # Correlated scalar subqueries to avoid cartesian products
    enrollments_count = (
        select(func.count(Enrollment.id))
        .where(Enrollment.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("enrollments_count")
    )
    completed_courses_count = (
        select(func.count(Enrollment.id))
        .where(Enrollment.user_id == User.id, Enrollment.completed_at.isnot(None))
        .correlate(User)
        .scalar_subquery()
        .label("completed_courses_count")
    )
    threads_count = (
        select(func.count(CommunityThread.id))
        .where(CommunityThread.author_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("threads_count")
    )
    replies_count = (
        select(func.count(ThreadReply.id))
        .where(ThreadReply.author_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("replies_count")
    )
    solutions_count = (
        select(func.count(ThreadReply.id))
        .where(ThreadReply.author_id == User.id, ThreadReply.is_solution == True)  # noqa: E712
        .correlate(User)
        .scalar_subquery()
        .label("solutions_count")
    )
    certificates_count = (
        select(func.count(Certificate.id))
        .where(Certificate.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("certificates_count")
    )
    conversations_count = (
        select(func.count(ConversationParticipant.id))
        .where(
            ConversationParticipant.user_id == User.id,
        )
        .correlate(User)
        .scalar_subquery()
        .label("conversations_count")
    )
    last_seen_date = (
        select(func.max(UserDailyActivity.date))
        .where(UserDailyActivity.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("last_seen_date")
    )

    query = (
        db.query(
            User,
            enrollments_count,
            completed_courses_count,
            threads_count,
            replies_count,
            solutions_count,
            certificates_count,
            conversations_count,
            UserPoints.total_points,
            UserPoints.level,
            UserStreak.current_streak,
            last_seen_date,
        )
        .outerjoin(UserPoints, UserPoints.user_id == User.id)
        .outerjoin(UserStreak, UserStreak.user_id == User.id)
    )

    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)  # noqa: E712
    if search:
        search_term = f"%{search}%"
        query = query.filter((User.name.ilike(search_term)) | (User.email.ilike(search_term)))

    # Count total before pagination — use a separate count query for correctness
    count_query = db.query(User)
    if role is not None:
        count_query = count_query.filter(User.role == role)
    if is_active is not None:
        count_query = count_query.filter(User.is_active == is_active)  # noqa: E712
    if search:
        search_term = f"%{search}%"
        count_query = count_query.filter(
            (User.name.ilike(search_term)) | (User.email.ilike(search_term))
        )
    total = count_query.count()

    rows = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    user_responses = []
    for row in rows:
        user = row[0]
        stats = UserStats(
            enrollments_count=row[1] or 0,
            completed_courses_count=row[2] or 0,
            threads_count=row[3] or 0,
            replies_count=row[4] or 0,
            solutions_count=row[5] or 0,
            certificates_count=row[6] or 0,
            conversations_count=row[7] or 0,
            total_points=row[8] or 0,
            level=row[9] or 1,
            current_streak=row[10] or 0,
            last_activity_date=(row[11].isoformat() if row[11] else None),
        )
        user_responses.append(
            UserWithStats(
                id=str(user.id),
                email=user.email,
                name=user.name,
                role=user.role,
                is_active=user.is_active,
                avatar_url=user.avatar_url,
                created_at=user.created_at.isoformat() if user.created_at else None,
                stats=stats,
            )
        )

    return UserListResponse(total=total, users=user_responses)


@router.get("/users/{user_id}/details", response_model=UserDetailResponse)
async def get_user_details(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserDetailResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie znaleziony",
        )

    # Enrollments with course titles
    enrollment_rows = (
        db.query(Enrollment, Course.title)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(Enrollment.user_id == user_id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )

    enrollments = [
        EnrollmentDetail(
            course_id=str(enrollment.course_id),
            course_title=course_title,
            enrolled_at=enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else "",
            completed_at=enrollment.completed_at.isoformat() if enrollment.completed_at else None,
            last_accessed_at=enrollment.last_accessed_at.isoformat()
            if enrollment.last_accessed_at
            else None,
        )
        for enrollment, course_title in enrollment_rows
    ]

    # Recent threads (max 5)
    thread_rows = (
        db.query(CommunityThread)
        .filter(CommunityThread.author_id == user_id)
        .order_by(CommunityThread.created_at.desc())
        .limit(5)
        .all()
    )

    recent_threads = [
        ThreadSummary(
            id=str(thread.id),
            title=thread.title,
            category=thread.category,
            status=thread.status,
            reply_count=thread.reply_count,
            created_at=thread.created_at.isoformat() if thread.created_at else "",
        )
        for thread in thread_rows
    ]

    # Last activity — max of last enrollment access, last thread, last reply
    activity_dates = []

    last_enrollment_access = (
        db.query(func.max(Enrollment.last_accessed_at))
        .filter(Enrollment.user_id == user_id)
        .scalar()
    )
    if last_enrollment_access:
        activity_dates.append(last_enrollment_access)

    last_thread_date = (
        db.query(func.max(CommunityThread.created_at))
        .filter(CommunityThread.author_id == user_id)
        .scalar()
    )
    if last_thread_date:
        activity_dates.append(last_thread_date)

    last_reply_date = (
        db.query(func.max(ThreadReply.created_at)).filter(ThreadReply.author_id == user_id).scalar()
    )
    if last_reply_date:
        activity_dates.append(last_reply_date)

    last_activity_at = max(activity_dates).isoformat() if activity_dates else None

    return UserDetailResponse(
        enrollments=enrollments,
        recent_threads=recent_threads,
        last_activity_at=last_activity_at,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie znaleziony",
        )

    if request.name is not None:
        user.name = request.name
    if request.role is not None:
        user.role = request.role
    if request.is_active is not None:
        user.is_active = request.is_active

    user.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
