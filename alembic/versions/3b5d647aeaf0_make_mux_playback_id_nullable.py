"""make_mux_playback_id_nullable

Revision ID: 3b5d647aeaf0
Revises: f2526c1bf680
Create Date: 2026-01-17 19:09:29.917460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b5d647aeaf0'
down_revision: Union[str, None] = 'f2526c1bf680'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make mux_playback_id nullable in lessons table
    op.alter_column(
        'lessons',
        'mux_playback_id',
        existing_type=sa.String(),
        nullable=True
    )


def downgrade() -> None:
    # Revert mux_playback_id to not nullable
    # Note: This might fail if there are lessons without mux_playback_id
    op.alter_column(
        'lessons',
        'mux_playback_id',
        existing_type=sa.String(),
        nullable=False
    )
