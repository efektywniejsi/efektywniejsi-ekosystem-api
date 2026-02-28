from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# NullPool: every request opens a fresh connection and closes it immediately.
# With only ~2 active users this adds negligible latency (~100-200 ms on
# Neon cold-start) while allowing Neon compute to auto-suspend between
# requests — cutting CU-hours from ~2/day to ~0.3-0.5/day.
_engine_kwargs: dict = {"poolclass": NullPool}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
