"""add created_at indexes for dashboard stats query

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-03-01 23:00:00.000000

仪表盘 /stats 接口 counts_query 慢（~1.5s）的根因：
多张大表上 WHERE created_at >= today_start 缺少索引，导致全表扫描。
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'f51eb0272e9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_pt_resources_created_at', 'pt_resources', ['created_at'], unique=False)
    op.create_index('ix_unified_movies_created_at', 'unified_movies', ['created_at'], unique=False)
    op.create_index('ix_unified_tv_series_created_at', 'unified_tv_series', ['created_at'], unique=False)
    op.create_index('ix_unified_tv_series_updated_at', 'unified_tv_series', ['updated_at'], unique=False)
    op.create_index('ix_unified_persons_created_at', 'unified_persons', ['created_at'], unique=False)
    op.create_index('ix_subscriptions_created_at', 'subscriptions', ['created_at'], unique=False)
    op.create_index('ix_download_tasks_created_at', 'download_tasks', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_download_tasks_created_at', table_name='download_tasks')
    op.drop_index('ix_subscriptions_created_at', table_name='subscriptions')
    op.drop_index('ix_unified_persons_created_at', table_name='unified_persons')
    op.drop_index('ix_unified_tv_series_updated_at', table_name='unified_tv_series')
    op.drop_index('ix_unified_tv_series_created_at', table_name='unified_tv_series')
    op.drop_index('ix_unified_movies_created_at', table_name='unified_movies')
    op.drop_index('ix_pt_resources_created_at', table_name='pt_resources')
