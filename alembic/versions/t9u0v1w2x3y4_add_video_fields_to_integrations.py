"""add_video_fields_to_integrations

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2x3
Create Date: 2026-02-18 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t9u0v1w2x3y4"
down_revision: Union[str, None] = "s8t9u0v1w2x3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("integrations", sa.Column("mux_asset_id", sa.String(), nullable=True))
    op.add_column("integrations", sa.Column("mux_playback_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("integrations", "mux_playback_id")
    op.drop_column("integrations", "mux_asset_id")
