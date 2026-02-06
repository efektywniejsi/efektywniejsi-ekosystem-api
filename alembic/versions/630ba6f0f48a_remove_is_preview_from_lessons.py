"""remove_is_preview_from_lessons

Revision ID: 630ba6f0f48a
Revises: eba6ad16dd6e
Create Date: 2026-02-07 00:15:20.282241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '630ba6f0f48a'
down_revision: Union[str, None] = 'eba6ad16dd6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('lessons', 'is_preview')


def downgrade() -> None:
    op.add_column('lessons', sa.Column('is_preview', sa.BOOLEAN(), nullable=False, server_default='false'))
