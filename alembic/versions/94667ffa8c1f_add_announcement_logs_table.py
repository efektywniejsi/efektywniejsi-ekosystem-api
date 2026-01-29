"""add announcement_logs table

Revision ID: 94667ffa8c1f
Revises: f62d2e86c643
Create Date: 2026-01-29 23:36:30.221261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94667ffa8c1f'
down_revision: Union[str, None] = 'f62d2e86c643'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('announcement_logs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('body_html', sa.Text(), nullable=False),
    sa.Column('body_text', sa.Text(), nullable=False),
    sa.Column('sent_by', sa.Uuid(), nullable=False),
    sa.Column('total_recipients', sa.Integer(), nullable=False),
    sa.Column('sent_count', sa.Integer(), nullable=False),
    sa.Column('skipped_count', sa.Integer(), nullable=False),
    sa.Column('failed_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['sent_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_announcement_logs_id'), 'announcement_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_announcement_logs_id'), table_name='announcement_logs')
    op.drop_table('announcement_logs')
