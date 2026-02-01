import datetime as dt
import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserDailyActivity(Base):
    __tablename__ = "user_daily_activity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[dt.date] = mapped_column(index=True)
    last_seen_at: Mapped[dt.datetime] = mapped_column()

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_daily_activity_user_date"),)
