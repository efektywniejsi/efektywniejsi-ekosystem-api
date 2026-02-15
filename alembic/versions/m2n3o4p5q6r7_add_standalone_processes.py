"""add standalone processes

Revision ID: m2n3o4p5q6r7
Revises: l1m2n3o4p5q6
Create Date: 2026-02-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m2n3o4p5q6r7"
down_revision: str | None = "l1m2n3o4p5q6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_processes_id"), "processes", ["id"])
    op.create_index(op.f("ix_processes_slug"), "processes", ["slug"])
    op.create_index(op.f("ix_processes_is_published"), "processes", ["is_published"])

    op.create_table(
        "lesson_processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("context_note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("lesson_id", "process_id", name="uq_lesson_process"),
    )
    op.create_index(op.f("ix_lesson_processes_lesson_id"), "lesson_processes", ["lesson_id"])
    op.create_index(op.f("ix_lesson_processes_process_id"), "lesson_processes", ["process_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_processes_process_id"), table_name="lesson_processes")
    op.drop_index(op.f("ix_lesson_processes_lesson_id"), table_name="lesson_processes")
    op.drop_table("lesson_processes")
    op.drop_index(op.f("ix_processes_is_published"), table_name="processes")
    op.drop_index(op.f("ix_processes_slug"), table_name="processes")
    op.drop_index(op.f("ix_processes_id"), table_name="processes")
    op.drop_table("processes")
