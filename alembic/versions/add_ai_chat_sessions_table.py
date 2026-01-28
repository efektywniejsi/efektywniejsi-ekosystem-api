"""Add ai_chat_sessions table for persistent AI chat history

Revision ID: e1a2b3c4d5f6
Revises: d0b089c6a70f
Create Date: 2026-01-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "e1a2b3c4d5f6"
down_revision: Union[str, None] = "d0b089c6a70f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(10), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("messages", JSONB, nullable=False, server_default="[]"),
        sa.Column("pending_task_id", sa.String(255), nullable=True),
        sa.Column("pending_response", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_ai_chat_entity"),
    )
    op.create_index(op.f("ix_ai_chat_sessions_id"), "ai_chat_sessions", ["id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_chat_sessions_id"), table_name="ai_chat_sessions")
    op.drop_table("ai_chat_sessions")
