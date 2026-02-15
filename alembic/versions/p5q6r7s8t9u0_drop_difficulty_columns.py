"""drop_difficulty_columns

Revision ID: p5q6r7s8t9u0
Revises: o4p5q6r7s8t9
Create Date: 2026-02-15 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p5q6r7s8t9u0'
down_revision: Union[str, None] = 'o4p5q6r7s8t9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('courses', 'difficulty')
    op.drop_column('packages', 'difficulty')
    op.drop_column('implementation_packages', 'difficulty')


def downgrade() -> None:
    op.add_column(
        'courses',
        sa.Column('difficulty', sa.String(length=50), nullable=False, server_default='beginner'),
    )
    op.add_column(
        'packages',
        sa.Column('difficulty', sa.String(), nullable=False, server_default='beginner'),
    )
    op.add_column(
        'implementation_packages',
        sa.Column('difficulty', sa.String(), nullable=False, server_default='beginner'),
    )
