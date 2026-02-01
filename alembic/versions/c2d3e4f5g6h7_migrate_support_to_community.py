"""migrate_support_to_community

Revision ID: c2d3e4f5g6h7
Revises: a1b2c3d4e5f7
Create Date: 2026-02-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5g6h7'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old support tables
    op.drop_index(op.f('ix_ticket_messages_ticket_id'), table_name='ticket_messages')
    op.drop_index(op.f('ix_ticket_messages_id'), table_name='ticket_messages')
    op.drop_table('ticket_messages')
    op.drop_index('ix_support_tickets_user_status', table_name='support_tickets')
    op.drop_index('ix_support_tickets_status_priority', table_name='support_tickets')
    op.drop_index(op.f('ix_support_tickets_id'), table_name='support_tickets')
    op.drop_table('support_tickets')

    # Create community_threads table
    op.create_table(
        'community_threads',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reply_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resolved_by_id', sa.Uuid(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_community_threads_id'), 'community_threads', ['id'], unique=False)
    op.create_index('ix_community_threads_category_created', 'community_threads', ['category', 'created_at'], unique=False)
    op.create_index('ix_community_threads_author', 'community_threads', ['author_id'], unique=False)
    op.create_index('ix_community_threads_status', 'community_threads', ['status'], unique=False)
    op.create_index('ix_community_threads_pinned', 'community_threads', ['is_pinned'], unique=False)

    # Create thread_replies table
    op.create_table(
        'thread_replies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('thread_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_solution', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['thread_id'], ['community_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_thread_replies_id'), 'thread_replies', ['id'], unique=False)
    op.create_index('ix_thread_replies_thread', 'thread_replies', ['thread_id'], unique=False)
    op.create_index('ix_thread_replies_author', 'thread_replies', ['author_id'], unique=False)


def downgrade() -> None:
    # Drop community tables
    op.drop_index('ix_thread_replies_author', table_name='thread_replies')
    op.drop_index('ix_thread_replies_thread', table_name='thread_replies')
    op.drop_index(op.f('ix_thread_replies_id'), table_name='thread_replies')
    op.drop_table('thread_replies')
    op.drop_index('ix_community_threads_pinned', table_name='community_threads')
    op.drop_index('ix_community_threads_status', table_name='community_threads')
    op.drop_index('ix_community_threads_author', table_name='community_threads')
    op.drop_index('ix_community_threads_category_created', table_name='community_threads')
    op.drop_index(op.f('ix_community_threads_id'), table_name='community_threads')
    op.drop_table('community_threads')

    # Recreate support tables
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_support_tickets_id'), 'support_tickets', ['id'], unique=False)
    op.create_index('ix_support_tickets_status_priority', 'support_tickets', ['status', 'priority'], unique=False)
    op.create_index('ix_support_tickets_user_status', 'support_tickets', ['user_id', 'status'], unique=False)
    op.create_table(
        'ticket_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('ticket_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_admin_reply', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ticket_messages_id'), 'ticket_messages', ['id'], unique=False)
    op.create_index(op.f('ix_ticket_messages_ticket_id'), 'ticket_messages', ['ticket_id'], unique=False)
