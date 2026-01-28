"""Add sales_page_sections JSONB column to packages

Revision ID: f7a8b9c0d1e2
Revises: b5a4773e1df5
Create Date: 2026-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "b5a4773e1df5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("packages", sa.Column("sales_page_sections", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("packages", "sales_page_sections")
