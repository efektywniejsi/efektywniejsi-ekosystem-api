"""add_sales_windows_table

Revision ID: c76bee7811ba
Revises: 114eb9d6582c
Create Date: 2026-01-24 12:07:36.544291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c76bee7811ba'
down_revision: Union[str, None] = '114eb9d6582c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sales_window_status enum
    op.execute("CREATE TYPE saleswindowstatus AS ENUM ('upcoming', 'active', 'closed')")

    # Create sales_windows table
    op.create_table(
        'sales_windows',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('upcoming', 'active', 'closed', name='saleswindowstatus', create_type=False), nullable=False),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=False),
        sa.Column('landing_page_config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('early_bird_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('bundle_ids', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_sales_windows_id'), 'sales_windows', ['id'], unique=False)
    op.create_index(op.f('ix_sales_windows_name'), 'sales_windows', ['name'], unique=False)
    op.create_index(op.f('ix_sales_windows_status'), 'sales_windows', ['status'], unique=False)
    op.create_index(op.f('ix_sales_windows_starts_at'), 'sales_windows', ['starts_at'], unique=False)
    op.create_index(op.f('ix_sales_windows_ends_at'), 'sales_windows', ['ends_at'], unique=False)
    op.create_index(op.f('ix_sales_windows_created_at'), 'sales_windows', ['created_at'], unique=False)

    # Create composite indexes
    op.create_index('idx_sales_window_active_time', 'sales_windows', ['status', 'starts_at', 'ends_at'], unique=False)
    op.create_index('idx_sales_window_created', 'sales_windows', ['created_at', 'status'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_sales_window_created', table_name='sales_windows')
    op.drop_index('idx_sales_window_active_time', table_name='sales_windows')
    op.drop_index(op.f('ix_sales_windows_created_at'), table_name='sales_windows')
    op.drop_index(op.f('ix_sales_windows_ends_at'), table_name='sales_windows')
    op.drop_index(op.f('ix_sales_windows_starts_at'), table_name='sales_windows')
    op.drop_index(op.f('ix_sales_windows_status'), table_name='sales_windows')
    op.drop_index(op.f('ix_sales_windows_name'), table_name='sales_windows')
    op.drop_index(op.f('ix_sales_windows_id'), table_name='sales_windows')

    # Drop table
    op.drop_table('sales_windows')

    # Drop enum
    op.execute("DROP TYPE saleswindowstatus")
