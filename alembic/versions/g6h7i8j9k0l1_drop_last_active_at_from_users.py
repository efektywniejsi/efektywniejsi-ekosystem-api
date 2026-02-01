"""drop_last_active_at_from_users

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2026-02-01 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g6h7i8j9k0l1"
down_revision: str | None = "f5g6h7i8j9k0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_users_last_active_at"), table_name="users")
    op.drop_column("users", "last_active_at")


def downgrade() -> None:
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_users_last_active_at"), "users", ["last_active_at"], unique=False)
