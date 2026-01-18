"""add_lesson_status

Revision ID: 49f335edbf16
Revises: 3b5d647aeaf0
Create Date: 2026-01-18 12:28:31.916324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49f335edbf16'
down_revision: Union[str, None] = '3b5d647aeaf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create PostgreSQL enum type for lesson status
    lesson_status_enum = sa.Enum(
        'unavailable',
        'in_preparation',
        'available',
        name='lesson_status',
        create_type=True
    )
    lesson_status_enum.create(op.get_bind(), checkfirst=True)

    # Add status column to lessons table with default value 'available'
    op.add_column(
        'lessons',
        sa.Column('status', lesson_status_enum, nullable=False, server_default='available')
    )


def downgrade() -> None:
    # Remove status column from lessons table
    op.drop_column('lessons', 'status')

    # Drop the PostgreSQL enum type
    lesson_status_enum = sa.Enum(
        'unavailable',
        'in_preparation',
        'available',
        name='lesson_status',
        create_type=False
    )
    lesson_status_enum.drop(op.get_bind(), checkfirst=True)
