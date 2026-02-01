"""consolidate_thread_categories

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2026-02-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4f5g6h7i8j9"
down_revision: Union[str, None] = "d3e4f5g6h7i8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Consolidate 7 categories into 4:
    # pytania + kursy + wdrozenia -> pomoc
    # porady -> ogolne
    # showcase -> showcase (unchanged)
    # pomysly -> pomysly (unchanged)
    # ogolne -> ogolne (unchanged)
    op.execute(
        "UPDATE community_threads SET category = 'pomoc' "
        "WHERE category IN ('pytania', 'kursy', 'wdrozenia')"
    )
    op.execute(
        "UPDATE community_threads SET category = 'ogolne' "
        "WHERE category = 'porady'"
    )


def downgrade() -> None:
    # Best-effort revert: pomoc -> pytania (original default)
    op.execute(
        "UPDATE community_threads SET category = 'pytania' "
        "WHERE category = 'pomoc'"
    )
