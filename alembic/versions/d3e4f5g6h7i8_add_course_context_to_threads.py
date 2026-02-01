"""add_course_context_to_threads

Revision ID: d3e4f5g6h7i8
Revises: c2d3e4f5g6h7
Create Date: 2026-02-01 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3e4f5g6h7i8"
down_revision: Union[str, None] = "c2d3e4f5g6h7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "community_threads",
        sa.Column("course_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "community_threads",
        sa.Column("module_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "community_threads",
        sa.Column("lesson_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_community_threads_course_id",
        "community_threads",
        "courses",
        ["course_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_threads_module_id",
        "community_threads",
        "modules",
        ["module_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_community_threads_lesson_id",
        "community_threads",
        "lessons",
        ["lesson_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_community_threads_course",
        "community_threads",
        ["course_id"],
    )

    # Migrate legacy categories to new values
    op.execute(
        "UPDATE community_threads SET category = 'ogolne' WHERE category IN ('general', 'pakiety')"
    )


def downgrade() -> None:
    op.drop_index("ix_community_threads_course", table_name="community_threads")
    op.drop_constraint("fk_community_threads_lesson_id", "community_threads", type_="foreignkey")
    op.drop_constraint("fk_community_threads_module_id", "community_threads", type_="foreignkey")
    op.drop_constraint("fk_community_threads_course_id", "community_threads", type_="foreignkey")
    op.drop_column("community_threads", "lesson_id")
    op.drop_column("community_threads", "module_id")
    op.drop_column("community_threads", "course_id")

    # Revert legacy category migration
    op.execute(
        "UPDATE community_threads SET category = 'general' WHERE category = 'ogolne'"
    )
