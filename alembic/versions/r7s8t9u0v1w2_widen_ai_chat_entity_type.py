"""widen_ai_chat_entity_type

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
Create Date: 2026-02-16 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r7s8t9u0v1w2"
down_revision: Union[str, None] = "q6r7s8t9u0v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ai_chat_sessions",
        "entity_type",
        type_=sa.String(30),
        existing_type=sa.String(10),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "ai_chat_sessions",
        "entity_type",
        type_=sa.String(10),
        existing_type=sa.String(30),
        existing_nullable=False,
    )
