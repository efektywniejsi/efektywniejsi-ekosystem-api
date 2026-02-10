"""add_invoice_fields_to_orders

Revision ID: a8b9c0d1e2f3
Revises: 630ba6f0f48a
Create Date: 2026-02-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = '630ba6f0f48a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Invoice fields (Fakturownia integration)
    op.add_column('orders', sa.Column('fakturownia_invoice_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('invoice_number', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('invoice_token', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('invoice_issued_at', sa.DateTime(), nullable=True))

    # Buyer billing information (for B2B invoices)
    op.add_column('orders', sa.Column('buyer_tax_no', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('buyer_company_name', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('buyer_street', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('buyer_post_code', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('buyer_city', sa.String(), nullable=True))

    # Index for invoice lookup
    op.create_index(
        op.f('ix_orders_fakturownia_invoice_id'),
        'orders',
        ['fakturownia_invoice_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_orders_fakturownia_invoice_id'), table_name='orders')
    op.drop_column('orders', 'buyer_city')
    op.drop_column('orders', 'buyer_post_code')
    op.drop_column('orders', 'buyer_street')
    op.drop_column('orders', 'buyer_company_name')
    op.drop_column('orders', 'buyer_tax_no')
    op.drop_column('orders', 'invoice_issued_at')
    op.drop_column('orders', 'invoice_token')
    op.drop_column('orders', 'invoice_number')
    op.drop_column('orders', 'fakturownia_invoice_id')
