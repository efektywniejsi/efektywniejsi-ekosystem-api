"""Make modules polymorphic and add learning fields to implementation_packages

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2026-02-15 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "l1m2n3o4p5q6"
down_revision: str | None = "k0l1m2n3o4p5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Make modules.course_id nullable (polymorphic parent)
    op.alter_column(
        "modules",
        "course_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # 2. Add implementation_package_id FK to modules
    op.add_column(
        "modules",
        sa.Column("implementation_package_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_modules_implementation_package_id",
        "modules",
        ["implementation_package_id"],
    )
    op.create_foreign_key(
        "fk_modules_implementation_package_id",
        "modules",
        "implementation_packages",
        ["implementation_package_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Add CHECK constraint: exactly one parent must be set
    op.create_check_constraint(
        "chk_module_parent",
        "modules",
        "(course_id IS NOT NULL AND implementation_package_id IS NULL) "
        "OR (course_id IS NULL AND implementation_package_id IS NOT NULL)",
    )

    # 4. Add learning fields to implementation_packages
    op.add_column(
        "implementation_packages",
        sa.Column("estimated_hours", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "implementation_packages",
        sa.Column("learning_title", sa.Text(), nullable=True),
    )
    op.add_column(
        "implementation_packages",
        sa.Column("learning_description", sa.Text(), nullable=True),
    )
    op.add_column(
        "implementation_packages",
        sa.Column("learning_thumbnail_url", sa.Text(), nullable=True),
    )

    # 5. Add expires_at to implementation_package_enrollments
    op.add_column(
        "implementation_package_enrollments",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # Remove expires_at from enrollments
    op.drop_column("implementation_package_enrollments", "expires_at")

    # Remove learning fields from implementation_packages
    op.drop_column("implementation_packages", "learning_thumbnail_url")
    op.drop_column("implementation_packages", "learning_description")
    op.drop_column("implementation_packages", "learning_title")
    op.drop_column("implementation_packages", "estimated_hours")

    # Remove CHECK constraint
    op.drop_constraint("chk_module_parent", "modules", type_="check")

    # Remove implementation_package_id FK and column
    op.drop_constraint("fk_modules_implementation_package_id", "modules", type_="foreignkey")
    op.drop_index("ix_modules_implementation_package_id", table_name="modules")
    op.drop_column("modules", "implementation_package_id")

    # Make course_id NOT NULL again
    op.alter_column(
        "modules",
        "course_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
