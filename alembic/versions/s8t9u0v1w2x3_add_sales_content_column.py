"""add_sales_content_column

Revision ID: s8t9u0v1w2x3
Revises: r7s8t9u0v1w2
Create Date: 2026-02-17 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "s8t9u0v1w2x3"
down_revision: Union[str, None] = "r7s8t9u0v1w2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("sales_content", JSONB, nullable=True))
    op.add_column("implementation_packages", sa.Column("sales_content", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("implementation_packages", "sales_content")
    op.drop_column("courses", "sales_content")
