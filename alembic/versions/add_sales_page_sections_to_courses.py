"""Add sales_page_sections JSONB column to courses

Revision ID: b5a4773e1df5
Revises: c3d4e5f6g7h8
Create Date: 2026-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "b5a4773e1df5"
down_revision: Union[str, None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("sales_page_sections", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "sales_page_sections")
