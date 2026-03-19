"""Add original category fields to pt_resources

Revision ID: ae7ee06b0f4f
Revises: 003
Create Date: 2026-02-07 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae7ee06b0f4f'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加原始分类字段到 pt_resources 表
    op.add_column('pt_resources', sa.Column('original_category_id', sa.String(length=50), nullable=True, comment='站点原始分类ID'))
    op.add_column('pt_resources', sa.Column('original_category_name', sa.String(length=200), nullable=True, comment='站点原始分类名称'))
    op.add_column('pt_resources', sa.Column('subcategory', sa.String(length=100), nullable=True, comment='子分类/二级分类'))

    # 创建索引以提高查询性能
    op.create_index('ix_pt_resources_original_category_id', 'pt_resources', ['original_category_id'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_pt_resources_original_category_id', table_name='pt_resources')

    # 删除字段
    op.drop_column('pt_resources', 'subcategory')
    op.drop_column('pt_resources', 'original_category_name')
    op.drop_column('pt_resources', 'original_category_id')
