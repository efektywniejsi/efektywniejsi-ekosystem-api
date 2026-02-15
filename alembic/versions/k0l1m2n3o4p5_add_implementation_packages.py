"""Add implementation_packages tables and update order_items

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2026-02-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "k0l1m2n3o4p5"
down_revision: str | None = "j9k0l1m2n3o4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create implementation_packages table
    op.create_table(
        "implementation_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("original_price", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False, server_default="PLN"),
        sa.Column("difficulty", sa.String(), nullable=False, server_default="beginner"),
        sa.Column("total_time_saved", sa.String(), nullable=True),
        sa.Column("tools", sa.String(), nullable=False, server_default="[]"),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sales_page_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_implementation_packages_id"), "implementation_packages", ["id"])
    op.create_index(op.f("ix_implementation_packages_slug"), "implementation_packages", ["slug"], unique=True)
    op.create_index(op.f("ix_implementation_packages_category"), "implementation_packages", ["category"])
    op.create_index(op.f("ix_implementation_packages_is_published"), "implementation_packages", ["is_published"])
    op.create_index(op.f("ix_implementation_packages_is_featured"), "implementation_packages", ["is_featured"])

    # 2. Create implementation_package_processes table
    op.create_table(
        "implementation_package_processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["implementation_packages.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_implementation_package_processes_id"),
        "implementation_package_processes",
        ["id"],
    )
    op.create_index(
        op.f("ix_implementation_package_processes_package_id"),
        "implementation_package_processes",
        ["package_id"],
    )

    # 3. Create implementation_package_enrollments table
    op.create_table(
        "implementation_package_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["implementation_packages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "package_id", name="uq_user_impl_package_enrollment"),
    )
    op.create_index(
        op.f("ix_implementation_package_enrollments_id"),
        "implementation_package_enrollments",
        ["id"],
    )
    op.create_index(
        op.f("ix_implementation_package_enrollments_user_id"),
        "implementation_package_enrollments",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_implementation_package_enrollments_package_id"),
        "implementation_package_enrollments",
        ["package_id"],
    )
    op.create_index(
        op.f("ix_implementation_package_enrollments_order_id"),
        "implementation_package_enrollments",
        ["order_id"],
    )
    op.create_index(
        "ix_impl_pkg_enrollments_user_package",
        "implementation_package_enrollments",
        ["user_id", "package_id"],
    )

    # 4. Modify order_items: add implementation_package_id, make package_id nullable
    op.alter_column(
        "order_items",
        "package_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "order_items",
        sa.Column("implementation_package_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_order_items_implementation_package_id"),
        "order_items",
        ["implementation_package_id"],
    )
    op.create_foreign_key(
        "fk_order_items_implementation_package_id",
        "order_items",
        "implementation_packages",
        ["implementation_package_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Remove FK and column from order_items
    op.drop_constraint("fk_order_items_implementation_package_id", "order_items", type_="foreignkey")
    op.drop_index(op.f("ix_order_items_implementation_package_id"), table_name="order_items")
    op.drop_column("order_items", "implementation_package_id")
    op.alter_column(
        "order_items",
        "package_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    # Drop tables in reverse dependency order
    op.drop_index("ix_impl_pkg_enrollments_user_package", table_name="implementation_package_enrollments")
    op.drop_index(op.f("ix_implementation_package_enrollments_order_id"), table_name="implementation_package_enrollments")
    op.drop_index(op.f("ix_implementation_package_enrollments_package_id"), table_name="implementation_package_enrollments")
    op.drop_index(op.f("ix_implementation_package_enrollments_user_id"), table_name="implementation_package_enrollments")
    op.drop_index(op.f("ix_implementation_package_enrollments_id"), table_name="implementation_package_enrollments")
    op.drop_table("implementation_package_enrollments")

    op.drop_index(op.f("ix_implementation_package_processes_package_id"), table_name="implementation_package_processes")
    op.drop_index(op.f("ix_implementation_package_processes_id"), table_name="implementation_package_processes")
    op.drop_table("implementation_package_processes")

    op.drop_index(op.f("ix_implementation_packages_is_featured"), table_name="implementation_packages")
    op.drop_index(op.f("ix_implementation_packages_is_published"), table_name="implementation_packages")
    op.drop_index(op.f("ix_implementation_packages_category"), table_name="implementation_packages")
    op.drop_index(op.f("ix_implementation_packages_slug"), table_name="implementation_packages")
    op.drop_index(op.f("ix_implementation_packages_id"), table_name="implementation_packages")
    op.drop_table("implementation_packages")
