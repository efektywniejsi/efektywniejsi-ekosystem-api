"""add_video_url_to_packages

Revision ID: 114eb9d6582c
Revises: 9761bc484020
Create Date: 2026-01-21 19:36:49.689458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '114eb9d6582c'
down_revision: Union[str, None] = '9761bc484020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add video_url column to packages table
    op.add_column('packages', sa.Column('video_url', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove video_url column from packages table
    op.drop_column('packages', 'video_url')
