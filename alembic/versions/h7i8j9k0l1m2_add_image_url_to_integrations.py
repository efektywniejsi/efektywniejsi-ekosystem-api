"""add_image_url_to_integrations

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2026-02-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h7i8j9k0l1m2"
down_revision: str | None = "b1c2d3e4f5g6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("integrations", sa.Column("image_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("integrations", "image_url")
