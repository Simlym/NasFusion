"""add unified_adult table

Revision ID: a1b2c3d4e5f6
Revises: 56548afe91a9
Create Date: 2026-02-07 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '56548afe91a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 unified_adult 统一成人资源表"""
    op.create_table('unified_adult',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),

        # 核心标识
        sa.Column('product_number', sa.String(length=100), nullable=True, comment='产品番号(如: nsps485)'),
        sa.Column('dmm_url', sa.Text(), nullable=True, comment='DMM页面URL'),
        sa.Column('pt_resource_id', sa.Integer(), nullable=True, comment='关联的PT资源ID（简化模式）'),

        # 标题
        sa.Column('title', sa.String(length=1000), nullable=False, comment='标题'),
        sa.Column('original_title', sa.String(length=1000), nullable=True, comment='原始标题（日文）'),

        # 基础信息
        sa.Column('release_date', sa.Date(), nullable=True, comment='发行日期'),
        sa.Column('duration', sa.String(length=50), nullable=True, comment='时长'),
        sa.Column('year', sa.Integer(), nullable=True, comment='年份'),

        # 制作信息
        sa.Column('maker', sa.String(length=200), nullable=True, comment='制作商'),
        sa.Column('label', sa.String(length=200), nullable=True, comment='发行商/厂牌'),
        sa.Column('series', sa.String(length=500), nullable=True, comment='系列'),
        sa.Column('director', sa.String(length=200), nullable=True, comment='导演'),

        # 人员
        sa.Column('actresses', sa.JSON(), nullable=True, comment='演员列表，JSON数组'),

        # 分类/标签
        sa.Column('genres', sa.JSON(), nullable=True, comment='类型/关键词 JSON数组'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签 JSON数组'),

        # 内容描述
        sa.Column('overview', sa.Text(), nullable=True, comment='简介/描述'),

        # 评分
        sa.Column('rating', sa.DECIMAL(precision=3, scale=1), nullable=True, comment='评分'),

        # 图片
        sa.Column('poster_url', sa.Text(), nullable=True, comment='封面URL（主图）'),
        sa.Column('backdrop_url', sa.Text(), nullable=True, comment='背景图URL'),
        sa.Column('image_list', sa.JSON(), nullable=True, comment='预览图列表，JSON数组'),

        # PT资源统计
        sa.Column('pt_resource_count', sa.Integer(), nullable=False, default=0, comment='关联的PT资源数量'),
        sa.Column('has_free_resource', sa.Boolean(), nullable=False, default=False, comment='是否有Free资源'),
        sa.Column('best_quality', sa.String(length=20), nullable=True, comment='最佳质量：4K/1080P等'),
        sa.Column('best_seeder_count', sa.Integer(), nullable=False, default=0, comment='最高做种数'),
        sa.Column('last_resource_updated_at', sa.DateTime(timezone=True), nullable=True, comment='PT资源最后更新时间'),

        # 本地文件
        sa.Column('local_file_count', sa.Integer(), nullable=False, default=0, comment='本地文件数量'),
        sa.Column('has_local', sa.Boolean(), nullable=False, default=False, comment='是否有本地文件'),
        sa.Column('local_images_dir', sa.String(length=500), nullable=True, comment='本地图片目录'),

        # 元数据管理
        sa.Column('detail_loaded', sa.Boolean(), nullable=False, default=False, comment='详情是否已加载（DMM数据）'),
        sa.Column('detail_loaded_at', sa.DateTime(timezone=True), nullable=True, comment='详情加载时间'),
        sa.Column('metadata_source', sa.String(length=20), nullable=True, comment='元数据来源：dmm/pt_resource'),

        # 原始数据
        sa.Column('raw_dmm_data', sa.JSON(), nullable=True, comment='DMM原始数据JSON'),

        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index(op.f('ix_unified_adult_product_number'), 'unified_adult', ['product_number'], unique=True)
    op.create_index(op.f('ix_unified_adult_pt_resource_id'), 'unified_adult', ['pt_resource_id'], unique=False)
    op.create_index(op.f('ix_unified_adult_release_date'), 'unified_adult', ['release_date'], unique=False)
    op.create_index(op.f('ix_unified_adult_year'), 'unified_adult', ['year'], unique=False)
    op.create_index(op.f('ix_unified_adult_has_free_resource'), 'unified_adult', ['has_free_resource'], unique=False)


def downgrade() -> None:
    """删除 unified_adult 表"""
    op.drop_index(op.f('ix_unified_adult_has_free_resource'), table_name='unified_adult')
    op.drop_index(op.f('ix_unified_adult_year'), table_name='unified_adult')
    op.drop_index(op.f('ix_unified_adult_release_date'), table_name='unified_adult')
    op.drop_index(op.f('ix_unified_adult_pt_resource_id'), table_name='unified_adult')
    op.drop_index(op.f('ix_unified_adult_product_number'), table_name='unified_adult')
    op.drop_table('unified_adult')
