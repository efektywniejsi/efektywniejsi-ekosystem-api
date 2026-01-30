"""add_settings_fields_to_users

Revision ID: 083bb7bd54ca
Revises: e1a2b3c4d5f6
Create Date: 2026-01-29 17:45:43.475595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '083bb7bd54ca'
down_revision: Union[str, None] = 'e1a2b3c4d5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('notification_preferences', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_users_stripe_customer_id'), 'users', ['stripe_customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_stripe_customer_id'), table_name='users')
    op.drop_column('users', 'notification_preferences')
    op.drop_column('users', 'stripe_customer_id')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'avatar_url')
