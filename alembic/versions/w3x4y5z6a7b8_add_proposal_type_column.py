"""add_proposal_type_column

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-03-28 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "w3x4y5z6a7b8"
down_revision: str | None = "v2w3x4y5z6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "integration_proposals",
        sa.Column(
            "proposal_type",
            sa.String(),
            nullable=False,
            server_default=sa.text("'integration'"),
        ),
    )
    op.create_index(
        "ix_integration_proposals_proposal_type",
        "integration_proposals",
        ["proposal_type"],
    )
    # Backfill: rows with category='Proces' are process proposals
    op.execute(
        "UPDATE integration_proposals SET proposal_type = 'process', category = NULL "
        "WHERE category = 'Proces'"
    )
    op.create_check_constraint(
        "ck_proposal_type_valid",
        "integration_proposals",
        "proposal_type IN ('integration', 'process')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_proposal_type_valid",
        "integration_proposals",
        type_="check",
    )
    op.drop_index(
        "ix_integration_proposals_proposal_type",
        table_name="integration_proposals",
    )
    op.drop_column("integration_proposals", "proposal_type")
