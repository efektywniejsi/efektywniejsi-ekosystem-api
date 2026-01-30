"""add_notifications_table

Revision ID: f62d2e86c643
Revises: 083bb7bd54ca
Create Date: 2026-01-29 18:11:19.269260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f62d2e86c643'
down_revision: Union[str, None] = '083bb7bd54ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('notification_type', sa.String(length=50), nullable=False),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('course_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
