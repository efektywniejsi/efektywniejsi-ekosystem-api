"""add_mermaid_and_code_snippets

Revision ID: u1v2w3x4y5z6
Revises: t9u0v1w2x3y4
Create Date: 2026-02-27 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, None] = "t9u0v1w2x3y4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("processes", sa.Column("mermaid_diagram", sa.Text(), nullable=True))
    op.add_column(
        "processes",
        sa.Column("code_snippets", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column("code_snippets", sa.dialects.postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lessons", "code_snippets")
    op.drop_column("processes", "code_snippets")
    op.drop_column("processes", "mermaid_diagram")
