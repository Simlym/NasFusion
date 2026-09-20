"""add durable workflow events

Revision ID: 5bb170d6737e
Revises: f7a8b9c0d1e2
Create Date: 2026-09-21 00:08:56.032366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.core.db_types import JSON, TZDateTime


# revision identifiers, used by Alembic.
revision: str = '5bb170d6737e'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('workflow_events',
    sa.Column('business_key', sa.String(length=160), nullable=False),
    sa.Column('event_type', sa.String(length=80), nullable=False),
    sa.Column('payload', JSON(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('execution_id', sa.Integer(), nullable=True),
    sa.Column('delivered_at', TZDateTime(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', TZDateTime(), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
    sa.Column('created_at', TZDateTime(), nullable=False, comment='创建时间'),
    sa.Column('updated_at', TZDateTime(), nullable=False, comment='更新时间'),
    sa.ForeignKeyConstraint(['execution_id'], ['task_executions.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('business_key')
    )
    op.create_index(op.f('ix_workflow_events_id'), 'workflow_events', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_events_status'), 'workflow_events', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_events_status'), table_name='workflow_events')
    op.drop_index(op.f('ix_workflow_events_id'), table_name='workflow_events')
    op.drop_table('workflow_events')
