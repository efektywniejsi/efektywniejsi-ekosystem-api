"""add_last_active_at_to_users

Revision ID: 73bb4407ac83
Revises: 7ddb451f0360
Create Date: 2026-01-31 13:59:54.118373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73bb4407ac83'
down_revision: Union[str, None] = '7ddb451f0360'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_active_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_last_active_at'), 'users', ['last_active_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_last_active_at'), table_name='users')
    op.drop_column('users', 'last_active_at')
