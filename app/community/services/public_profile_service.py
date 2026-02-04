from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.community.models.reply import ThreadReply
from app.community.models.thread import CommunityThread
from app.community.schemas.public_profile import (
    CommunityActivity,
    PublicCourseInfo,
    PublicProfileResponse,
)
from app.courses.models.certificate import Certificate
from app.courses.models.course import Course
from app.courses.models.enrollment import Enrollment
from app.courses.models.gamification import UserPoints, UserStreak


class PublicProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_public_profile(self, user_id: UUID) -> PublicProfileResponse:
        user = (
            self.db.query(User)
            .filter(User.id == user_id, User.is_active == True)  # noqa: E712
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Użytkownik nie został znaleziony",
            )

        courses = self._get_enrolled_courses(user_id)
        community_activity = self._get_community_activity(user_id)
        certificates_count = self._get_certificates_count(user_id)
        gamification = self._get_gamification(user_id)

        return PublicProfileResponse(
            id=user.id,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
            member_since=user.created_at,
            courses=courses,
            completed_courses_count=sum(1 for c in courses if c.is_completed),
            community_activity=community_activity,
            certificates_count=certificates_count,
            level=gamification["level"],
            total_points=gamification["total_points"],
            current_streak=gamification["current_streak"],
        )

    def _get_enrolled_courses(self, user_id: UUID) -> list[PublicCourseInfo]:
        enrollments = (
            self.db.query(Enrollment)
            .join(Course, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == user_id, Course.is_published == True)  # noqa: E712
            .all()
        )
        return [
            PublicCourseInfo(
                id=enrollment.course.id,
                title=enrollment.course.title,
                slug=enrollment.course.slug,
                thumbnail_url=enrollment.course.thumbnail_url,
                difficulty=enrollment.course.difficulty,
                is_completed=enrollment.completed_at is not None,
            )
            for enrollment in enrollments
            if enrollment.course
        ]

    def _get_community_activity(self, user_id: UUID) -> CommunityActivity:
        thread_count = (
            self.db.query(func.count(CommunityThread.id))
            .filter(CommunityThread.author_id == user_id)
            .scalar()
            or 0
        )
        reply_count = (
            self.db.query(func.count(ThreadReply.id))
            .filter(ThreadReply.author_id == user_id)
            .scalar()
            or 0
        )
        solution_count = (
            self.db.query(func.count(ThreadReply.id))
            .filter(
                ThreadReply.author_id == user_id,
                ThreadReply.is_solution == True,  # noqa: E712
            )
            .scalar()
            or 0
        )
        return CommunityActivity(
            thread_count=thread_count,
            reply_count=reply_count,
            solution_count=solution_count,
        )

    def _get_gamification(self, user_id: UUID) -> dict:
        points = self.db.query(UserPoints).filter(UserPoints.user_id == user_id).first()
        streak = self.db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
        return {
            "level": points.level if points else 1,
            "total_points": points.total_points if points else 0,
            "current_streak": streak.current_streak if streak else 0,
        }

    def _get_certificates_count(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Certificate.id))
            .filter(Certificate.user_id == user_id)
            .scalar()
            or 0
        )
