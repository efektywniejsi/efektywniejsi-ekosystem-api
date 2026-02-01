"""add_thread_tags_and_attachments

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2026-02-01 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5g6h7i8j9k0"
down_revision: Union[str, None] = "e4f5g6h7i8j9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Thread tags table
    op.create_table(
        "community_thread_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_thread_tags_id", "community_thread_tags", ["id"])
    op.create_index("ix_community_thread_tags_name", "community_thread_tags", ["name"], unique=True)

    # Thread tag associations table
    op.create_table(
        "community_thread_tag_associations",
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["community_threads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["community_thread_tags.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("thread_id", "tag_id"),
    )
    op.create_index(
        "ix_thread_tag_assoc_thread",
        "community_thread_tag_associations",
        ["thread_id"],
    )
    op.create_index(
        "ix_thread_tag_assoc_tag",
        "community_thread_tag_associations",
        ["tag_id"],
    )

    # Thread attachments table
    op.create_table(
        "community_thread_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("uploader_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["community_threads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploader_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_thread_attachments_id", "community_thread_attachments", ["id"])
    op.create_index("ix_thread_attachments_thread", "community_thread_attachments", ["thread_id"])
    op.create_index(
        "ix_thread_attachments_uploader", "community_thread_attachments", ["uploader_id"]
    )


def downgrade() -> None:
    op.drop_table("community_thread_attachments")
    op.drop_table("community_thread_tag_associations")
    op.drop_table("community_thread_tags")
