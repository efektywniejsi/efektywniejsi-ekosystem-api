"""Add process_integrations table

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-02-11 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i8j9k0l1m2n3"
down_revision: str | None = "h7i8j9k0l1m2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # process_integrations: Junction table linking integrations to package processes
    op.create_table(
        "process_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("context_note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["process_id"], ["package_processes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integrations.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "process_id", "integration_id", name="uq_process_integration"
        ),
    )
    op.create_index(
        op.f("ix_process_integrations_process_id"),
        "process_integrations",
        ["process_id"],
    )
    op.create_index(
        op.f("ix_process_integrations_integration_id"),
        "process_integrations",
        ["integration_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_process_integrations_integration_id"),
        table_name="process_integrations",
    )
    op.drop_index(
        op.f("ix_process_integrations_process_id"),
        table_name="process_integrations",
    )
    op.drop_table("process_integrations")
