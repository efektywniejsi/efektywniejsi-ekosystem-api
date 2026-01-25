"""add_bundle_course_items

Revision ID: a1b2c3d4e5f6
Revises: c76bee7811ba
Create Date: 2026-01-24 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c76bee7811ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bundle_course_items table to link bundles with courses
    op.create_table(
        'bundle_course_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('bundle_id', sa.Uuid(), nullable=False),
        sa.Column('course_id', sa.Uuid(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['bundle_id'], ['packages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bundle_id', 'course_id', name='uq_bundle_course')
    )

    # Create indexes
    op.create_index(op.f('ix_bundle_course_items_id'), 'bundle_course_items', ['id'], unique=False)
    op.create_index(op.f('ix_bundle_course_items_bundle_id'), 'bundle_course_items', ['bundle_id'], unique=False)
    op.create_index(op.f('ix_bundle_course_items_course_id'), 'bundle_course_items', ['course_id'], unique=False)
    op.create_index('ix_bundle_course_items_bundle_course', 'bundle_course_items', ['bundle_id', 'course_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_bundle_course_items_bundle_course', table_name='bundle_course_items')
    op.drop_index(op.f('ix_bundle_course_items_course_id'), table_name='bundle_course_items')
    op.drop_index(op.f('ix_bundle_course_items_bundle_id'), table_name='bundle_course_items')
    op.drop_index(op.f('ix_bundle_course_items_id'), table_name='bundle_course_items')

    # Drop table
    op.drop_table('bundle_course_items')
