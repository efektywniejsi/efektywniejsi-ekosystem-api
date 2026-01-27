"""Add content_type to courses

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("content_type", sa.String(), nullable=False, server_default="course"),
    )
    op.create_index("ix_courses_content_type", "courses", ["content_type"])


def downgrade() -> None:
    op.drop_index("ix_courses_content_type", table_name="courses")
    op.drop_column("courses", "content_type")
