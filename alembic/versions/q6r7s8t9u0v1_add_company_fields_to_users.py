"""add_company_fields_to_users

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-02-16 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q6r7s8t9u0v1"
down_revision: Union[str, None] = "p5q6r7s8t9u0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("buyer_tax_no", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("buyer_company_name", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("buyer_street", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("buyer_post_code", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("buyer_city", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "buyer_city")
    op.drop_column("users", "buyer_post_code")
    op.drop_column("users", "buyer_street")
    op.drop_column("users", "buyer_company_name")
    op.drop_column("users", "buyer_tax_no")
