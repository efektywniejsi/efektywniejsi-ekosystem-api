"""Add access_duration_days to bundle_course_items

Revision ID: d4e5f6g7h8i9
Revises: b5a4773e1df5
Create Date: 2026-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "b5a4773e1df5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bundle_course_items",
        sa.Column("access_duration_days", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bundle_course_items", "access_duration_days")
