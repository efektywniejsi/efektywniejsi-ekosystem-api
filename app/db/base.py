# Import all SQLAlchemy models here for Alembic auto-generation
# This file is imported in alembic/env.py for auto-generating migrations

from app.auth.models.user import User  # noqa: F401
from app.db.session import Base  # noqa: F401

# When you add new models, import them here
# Example:
# from app.catalog.models.course import Course  # noqa: F401
