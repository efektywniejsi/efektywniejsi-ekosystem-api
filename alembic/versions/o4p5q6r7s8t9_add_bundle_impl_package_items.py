"""add_bundle_implementation_package_items

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
Create Date: 2026-02-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o4p5q6r7s8t9'
down_revision: Union[str, None] = 'n3o4p5q6r7s8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bundle_implementation_package_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('bundle_id', sa.Uuid(), nullable=False),
        sa.Column('implementation_package_id', sa.Uuid(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('access_duration_days', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['bundle_id'], ['packages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['implementation_package_id'],
            ['implementation_packages.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'bundle_id', 'implementation_package_id', name='uq_bundle_impl_package'
        ),
    )

    op.create_index(
        op.f('ix_bundle_impl_pkg_items_id'),
        'bundle_implementation_package_items',
        ['id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_bundle_impl_pkg_items_bundle_id'),
        'bundle_implementation_package_items',
        ['bundle_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_bundle_impl_pkg_items_impl_pkg_id'),
        'bundle_implementation_package_items',
        ['implementation_package_id'],
        unique=False,
    )
    op.create_index(
        'ix_bundle_impl_pkg_items_bundle_impl',
        'bundle_implementation_package_items',
        ['bundle_id', 'implementation_package_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_bundle_impl_pkg_items_bundle_impl',
        table_name='bundle_implementation_package_items',
    )
    op.drop_index(
        op.f('ix_bundle_impl_pkg_items_impl_pkg_id'),
        table_name='bundle_implementation_package_items',
    )
    op.drop_index(
        op.f('ix_bundle_impl_pkg_items_bundle_id'),
        table_name='bundle_implementation_package_items',
    )
    op.drop_index(
        op.f('ix_bundle_impl_pkg_items_id'),
        table_name='bundle_implementation_package_items',
    )

    op.drop_table('bundle_implementation_package_items')
