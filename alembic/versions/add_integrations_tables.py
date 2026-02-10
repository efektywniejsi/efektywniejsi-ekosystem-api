"""Add integrations library tables

Revision ID: b1c2d3e4f5g6
Revises: a8b9c0d1e2f3
Create Date: 2026-02-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # integrations: Main table for integration entries
    op.create_table(
        "integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("auth_guide", sa.Text(), nullable=True),
        sa.Column("official_docs_url", sa.String(500), nullable=True),
        sa.Column("video_tutorial_url", sa.String(500), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_integrations_id"), "integrations", ["id"])
    op.create_index(op.f("ix_integrations_slug"), "integrations", ["slug"])
    op.create_index(op.f("ix_integrations_category"), "integrations", ["category"])
    op.create_index(op.f("ix_integrations_is_published"), "integrations", ["is_published"])

    # integration_types: Junction table for integration types (API, OAuth 2.0, MCP)
    op.create_table(
        "integration_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("type_name", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integrations.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("integration_id", "type_name", name="uq_integration_type"),
    )
    op.create_index(
        op.f("ix_integration_types_integration_id"),
        "integration_types",
        ["integration_id"],
    )

    # lesson_integrations: Junction table linking integrations to lessons
    op.create_table(
        "lesson_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("context_note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integrations.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "lesson_id", "integration_id", name="uq_lesson_integration"
        ),
    )
    op.create_index(
        op.f("ix_lesson_integrations_lesson_id"),
        "lesson_integrations",
        ["lesson_id"],
    )
    op.create_index(
        op.f("ix_lesson_integrations_integration_id"),
        "lesson_integrations",
        ["integration_id"],
    )

    # integration_proposals: User-submitted integration suggestions
    op.create_table(
        "integration_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("official_docs_url", sa.String(500), nullable=True),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="pending"
        ),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"], ["users.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(op.f("ix_integration_proposals_id"), "integration_proposals", ["id"])
    op.create_index(
        op.f("ix_integration_proposals_status"), "integration_proposals", ["status"]
    )
    op.create_index(
        op.f("ix_integration_proposals_submitted_by_id"),
        "integration_proposals",
        ["submitted_by_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_integration_proposals_submitted_by_id"),
        table_name="integration_proposals",
    )
    op.drop_index(
        op.f("ix_integration_proposals_status"), table_name="integration_proposals"
    )
    op.drop_index(op.f("ix_integration_proposals_id"), table_name="integration_proposals")
    op.drop_table("integration_proposals")

    op.drop_index(
        op.f("ix_lesson_integrations_integration_id"),
        table_name="lesson_integrations",
    )
    op.drop_index(
        op.f("ix_lesson_integrations_lesson_id"), table_name="lesson_integrations"
    )
    op.drop_table("lesson_integrations")

    op.drop_index(
        op.f("ix_integration_types_integration_id"), table_name="integration_types"
    )
    op.drop_table("integration_types")

    op.drop_index(op.f("ix_integrations_is_published"), table_name="integrations")
    op.drop_index(op.f("ix_integrations_category"), table_name="integrations")
    op.drop_index(op.f("ix_integrations_slug"), table_name="integrations")
    op.drop_index(op.f("ix_integrations_id"), table_name="integrations")
    op.drop_table("integrations")
