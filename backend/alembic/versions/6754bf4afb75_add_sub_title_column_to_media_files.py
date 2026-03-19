"""add sub_title column to media_files

Revision ID: 6754bf4afb75
Revises: e1f2a3b4c5d6
Create Date: 2026-03-15 18:51:45.508632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6754bf4afb75'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 sub_title 列到 media_files 表
    op.add_column('media_files', sa.Column('sub_title', sa.String(length=500), nullable=True, comment='副标题（从PT资源复制，避免relationship问题）'))


def downgrade() -> None:
    # 删除 sub_title 列
    op.drop_column('media_files', 'sub_title')
