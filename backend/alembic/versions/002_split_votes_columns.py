"""split votes_count into source-specific columns

Revision ID: 002
Revises: 001
Create Date: 2026-01-24 11:01:00.000000

Changes:
- unified_movies: Replace votes_count with votes_tmdb, votes_douban, votes_imdb
- unified_tv_series: Replace votes_count with votes_tmdb, votes_douban, votes_imdb
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    安全迁移：处理两种场景
    1. 旧数据库：votes_count 存在，需要拆分
    2. 新数据库：已经是新结构（由 SQLAlchemy 自动创建），跳过
    """
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # === 处理 unified_movies 表 ===
    movies_columns = [col['name'] for col in inspector.get_columns('unified_movies')]

    # 检查是否需要迁移（旧结构有 votes_count，新结构有 votes_tmdb）
    if 'votes_count' in movies_columns and 'votes_tmdb' not in movies_columns:
        # 旧数据库：执行完整迁移
        op.add_column('unified_movies', sa.Column('votes_tmdb', sa.Integer(), nullable=True, comment='TMDB投票数'))
        op.add_column('unified_movies', sa.Column('votes_douban', sa.Integer(), nullable=True, comment='豆瓣投票数'))
        op.add_column('unified_movies', sa.Column('votes_imdb', sa.Integer(), nullable=True, comment='IMDB投票数'))

        # 迁移数据
        op.execute('UPDATE unified_movies SET votes_tmdb = votes_count WHERE votes_count IS NOT NULL')

        # 删除旧列
        op.drop_column('unified_movies', 'votes_count')
    elif 'votes_tmdb' in movies_columns:
        # 新数据库：已经是新结构，跳过
        print("unified_movies already has new structure (votes_tmdb exists), skipping migration")

    # === 处理 unified_tv_series 表 ===
    tv_columns = [col['name'] for col in inspector.get_columns('unified_tv_series')]

    if 'votes_count' in tv_columns and 'votes_tmdb' not in tv_columns:
        # 旧数据库：执行完整迁移
        op.add_column('unified_tv_series', sa.Column('votes_tmdb', sa.Integer(), nullable=True, comment='TMDB投票数'))
        op.add_column('unified_tv_series', sa.Column('votes_douban', sa.Integer(), nullable=True, comment='豆瓣投票数'))
        op.add_column('unified_tv_series', sa.Column('votes_imdb', sa.Integer(), nullable=True, comment='IMDB投票数'))

        # 迁移数据
        op.execute('UPDATE unified_tv_series SET votes_tmdb = votes_count WHERE votes_count IS NOT NULL')

        # 删除旧列
        op.drop_column('unified_tv_series', 'votes_count')
    elif 'votes_tmdb' in tv_columns:
        # 新数据库：已经是新结构，跳过
        print("unified_tv_series already has new structure (votes_tmdb exists), skipping migration")


def downgrade() -> None:
    # Add back votes_count column
    op.add_column('unified_tv_series', sa.Column('votes_count', sa.INTEGER(), nullable=True))

    # Migrate data: copy votes_tmdb back to votes_count
    op.execute('UPDATE unified_tv_series SET votes_count = votes_tmdb WHERE votes_tmdb IS NOT NULL')

    # Drop new columns
    op.drop_column('unified_tv_series', 'votes_imdb')
    op.drop_column('unified_tv_series', 'votes_douban')
    op.drop_column('unified_tv_series', 'votes_tmdb')

    # Add back votes_count column for movies
    op.add_column('unified_movies', sa.Column('votes_count', sa.INTEGER(), nullable=True))

    # Migrate data
    op.execute('UPDATE unified_movies SET votes_count = votes_tmdb WHERE votes_tmdb IS NOT NULL')

    # Drop new columns
    op.drop_column('unified_movies', 'votes_imdb')
    op.drop_column('unified_movies', 'votes_douban')
    op.drop_column('unified_movies', 'votes_tmdb')
