import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

_is_worker = os.environ.get("WORKER") == "true"

_engine_kwargs: dict = {"pool_pre_ping": True}

if _is_worker:
    # Worker: no persistent connections → allows Neon auto-suspend
    _engine_kwargs["poolclass"] = NullPool
else:
    # API: small pool so idle connections close and Neon can auto-suspend
    _engine_kwargs["pool_size"] = 2
    _engine_kwargs["max_overflow"] = 3
    _engine_kwargs["pool_recycle"] = 300  # close idle connections after 5 min

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
