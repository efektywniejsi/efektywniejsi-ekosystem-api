"""Add learning fields to courses

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("learning_title", sa.String(), nullable=True))
    op.add_column("courses", sa.Column("learning_description", sa.String(), nullable=True))
    op.add_column("courses", sa.Column("learning_thumbnail_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "learning_thumbnail_url")
    op.drop_column("courses", "learning_description")
    op.drop_column("courses", "learning_title")
