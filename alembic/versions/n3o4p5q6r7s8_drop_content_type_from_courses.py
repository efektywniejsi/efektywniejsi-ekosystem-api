"""drop content_type from courses

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-02-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n3o4p5q6r7s8"
down_revision: str | None = "m2n3o4p5q6r7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_courses_content_type", table_name="courses")
    op.drop_column("courses", "content_type")


def downgrade() -> None:
    op.add_column(
        "courses",
        sa.Column(
            "content_type",
            sa.String(),
            server_default="course",
            nullable=False,
        ),
    )
    op.create_index("ix_courses_content_type", "courses", ["content_type"])
