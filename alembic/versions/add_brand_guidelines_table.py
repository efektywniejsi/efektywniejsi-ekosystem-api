"""Add brand_guidelines table for AI generation

Revision ID: d0b089c6a70f
Revises: f7a8b9c0d1e2
Create Date: 2026-01-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d0b089c6a70f"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_guidelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tone", sa.String(), nullable=False, server_default=""),
        sa.Column("style", sa.String(), nullable=False, server_default=""),
        sa.Column("target_audience", sa.String(), nullable=False, server_default=""),
        sa.Column("unique_selling_proposition", sa.String(), nullable=False, server_default=""),
        sa.Column("language", sa.String(), nullable=False, server_default="pl"),
        sa.Column("avoid_phrases", sa.String(), nullable=False, server_default=""),
        sa.Column("preferred_phrases", sa.String(), nullable=False, server_default=""),
        sa.Column("company_description", sa.String(), nullable=False, server_default=""),
        sa.Column("additional_instructions", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_brand_guidelines_id"), "brand_guidelines", ["id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_brand_guidelines_id"), table_name="brand_guidelines")
    op.drop_table("brand_guidelines")
