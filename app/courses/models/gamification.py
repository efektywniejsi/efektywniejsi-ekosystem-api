import uuid
from datetime import UTC, date, datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    icon: Mapped[str | None] = mapped_column(default=None)
    points_reward: Mapped[int] = mapped_column(default=0)
    category: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    user_achievements = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Achievement(id={self.id}, code={self.code}, title={self.title})>"


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), index=True
    )
    earned_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    progress_value: Mapped[int | None] = mapped_column(default=0)

    user = relationship("User", backref="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

    def __repr__(self) -> str:
        return f"<UserAchievement(id={self.id}, user_id={self.user_id}, achievement_id={self.achievement_id})>"  # noqa: E501


class UserStreak(Base):
    __tablename__ = "user_streaks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    current_streak: Mapped[int] = mapped_column(default=0)
    longest_streak: Mapped[int] = mapped_column(default=0)
    last_activity_date: Mapped[date] = mapped_column(default=date.today)
    grace_period_used_at: Mapped[date | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", backref="streak", uselist=False)

    def __repr__(self) -> str:
        return f"<UserStreak(id={self.id}, user_id={self.user_id}, current={self.current_streak}, longest={self.longest_streak})>"  # noqa: E501


class UserPoints(Base):
    __tablename__ = "user_points"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    total_points: Mapped[int] = mapped_column(default=0)
    level: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", backref="points", uselist=False)

    def __repr__(self) -> str:
        return f"<UserPoints(id={self.id}, user_id={self.user_id}, total={self.total_points}, level={self.level})>"  # noqa: E501


class PointsHistory(Base):
    __tablename__ = "points_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    points: Mapped[int] = mapped_column()
    reason: Mapped[str] = mapped_column()
    reference_type: Mapped[str | None] = mapped_column(default=None)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)

    user = relationship("User", backref="points_history")

    def __repr__(self) -> str:
        return f"<PointsHistory(id={self.id}, user_id={self.user_id}, points={self.points}, reason={self.reason})>"  # noqa: E501
