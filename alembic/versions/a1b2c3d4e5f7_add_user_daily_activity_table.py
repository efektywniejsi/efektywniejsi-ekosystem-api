"""add_user_daily_activity_table

Revision ID: a1b2c3d4e5f7
Revises: 73bb4407ac83
Create Date: 2026-01-31 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = '73bb4407ac83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_daily_activity',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_daily_activity_user_date'),
    )
    op.create_index(op.f('ix_user_daily_activity_user_id'), 'user_daily_activity', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_daily_activity_date'), 'user_daily_activity', ['date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_daily_activity_date'), table_name='user_daily_activity')
    op.drop_index(op.f('ix_user_daily_activity_user_id'), table_name='user_daily_activity')
    op.drop_table('user_daily_activity')
