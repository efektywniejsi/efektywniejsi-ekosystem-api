"""add announcement_log_id to notifications

Revision ID: b3a1c7e9d402
Revises: 94667ffa8c1f
Create Date: 2026-01-29 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a1c7e9d402'
down_revision: Union[str, None] = '94667ffa8c1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notifications', sa.Column('announcement_log_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_notifications_announcement_log_id',
        'notifications',
        'announcement_logs',
        ['announcement_log_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_notifications_announcement_log_id', 'notifications', ['announcement_log_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_announcement_log_id', table_name='notifications')
    op.drop_constraint('fk_notifications_announcement_log_id', 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'announcement_log_id')
