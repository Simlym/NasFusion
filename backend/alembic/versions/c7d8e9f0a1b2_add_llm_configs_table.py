"""add llm_configs table

Revision ID: c7d8e9f0a1b2
Revises: 193dbdf95aa1
Create Date: 2026-04-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = '193dbdf95aa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 llm_configs 表
    op.create_table(
        'llm_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='配置名称'),
        sa.Column('provider', sa.String(length=50), nullable=False, comment='LLM供应商'),
        sa.Column('api_key', sa.Text(), nullable=False, comment='API密钥（加密存储）'),
        sa.Column('api_base', sa.String(length=500), nullable=True, comment='API基础URL'),
        sa.Column('proxy', sa.String(length=255), nullable=True, comment='代理服务器URL'),
        sa.Column('model', sa.String(length=100), nullable=False, comment='默认模型'),
        sa.Column('default_temperature', sa.String(length=10), nullable=False, server_default='0.7', comment='默认温度参数'),
        sa.Column('default_max_tokens', sa.Integer(), nullable=False, server_default='2048', comment='默认最大Token数'),
        sa.Column('default_top_p', sa.String(length=10), nullable=False, server_default='0.9', comment='默认Top-P参数'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1', comment='是否启用'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0', comment='排序顺序'),
        sa.Column('last_test_at', sa.DateTime(timezone=True), nullable=True, comment='最后测试时间'),
        sa.Column('last_test_result', sa.Text(), nullable=True, comment='最后测试结果'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ai_agent_configs 表添加 llm_config_id 外键列
    op.add_column(
        'ai_agent_configs',
        sa.Column('llm_config_id', sa.Integer(), nullable=True, comment='关联的全局LLM配置ID'),
    )
    op.create_foreign_key(
        'fk_ai_agent_configs_llm_config_id',
        'ai_agent_configs', 'llm_configs',
        ['llm_config_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # 移除外键和列
    op.drop_constraint('fk_ai_agent_configs_llm_config_id', 'ai_agent_configs', type_='foreignkey')
    op.drop_column('ai_agent_configs', 'llm_config_id')

    # 删除 llm_configs 表
    op.drop_table('llm_configs')
