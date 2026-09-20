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
    columns = [
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
    ]
    inspector = None if op.get_context().as_sql else sa.inspect(op.get_bind())
    if inspector is not None and inspector.has_table('llm_configs'):
        # 兼容开发库曾由 create_all 提前建表的情况；结构不符时不能直接跳过。
        actual = {column['name']: column for column in inspector.get_columns('llm_configs')}
        for expected in columns:
            _check_column('llm_configs', actual.get(expected.name), expected)
        if inspector.get_pk_constraint('llm_configs')['constrained_columns'] != ['id']:
            raise RuntimeError('llm_configs 主键不匹配，停止迁移')
    else:
        op.create_table('llm_configs', *columns, sa.PrimaryKeyConstraint('id'))

    # ai_agent_configs 表添加 llm_config_id 外键列
    column = sa.Column('llm_config_id', sa.Integer(), nullable=True, comment='关联的全局LLM配置ID')
    existing = next((item for item in inspector.get_columns('ai_agent_configs')
                     if item['name'] == column.name), None) if inspector else None
    if existing is not None:
        _check_column('ai_agent_configs', existing, column)
    foreign_keys = _get_foreign_keys(inspector)
    for fk in foreign_keys:
        if fk['referred_table'] != 'llm_configs' or fk['referred_columns'] != ['id']:
            raise RuntimeError('ai_agent_configs.llm_config_id 的外键目标不匹配')
    correct_fk = len(foreign_keys) == 1 and foreign_keys[0].get('options', {}).get('ondelete') == 'SET NULL'
    if existing is not None and correct_fk:
        return
    with op.batch_alter_table('ai_agent_configs', naming_convention=FK_NAMING) as batch:
        if existing is None:
            batch.add_column(column)
        for fk in foreign_keys:
            batch.drop_constraint(fk['name'] or REFLECTED_FK_NAME, type_='foreignkey')
        batch.create_foreign_key(
            'fk_ai_agent_configs_llm_config_id', 'llm_configs', ['llm_config_id'], ['id'], ondelete='SET NULL',
        )


FK_NAMING = {'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s'}
REFLECTED_FK_NAME = 'fk_ai_agent_configs_llm_config_id_llm_configs'


def _check_column(table, actual, expected):
    # SQLite 不强制字符串长度；create_all 的 Python 默认值也不同于迁移的服务端默认值。
    if (actual is None or actual['type']._type_affinity is not expected.type._type_affinity
            or actual['nullable'] != expected.nullable):
        raise RuntimeError(f'{table}.{expected.name} 已存在但结构不兼容，停止迁移')


def _get_foreign_keys(inspector):
    if inspector is None:
        return []
    return [fk for fk in inspector.get_foreign_keys('ai_agent_configs')
            if fk['constrained_columns'] == ['llm_config_id']]


def downgrade() -> None:
    # 移除外键和列
    inspector = None if op.get_context().as_sql else sa.inspect(op.get_bind())
    foreign_keys = _get_foreign_keys(inspector)
    with op.batch_alter_table('ai_agent_configs', naming_convention=FK_NAMING) as batch:
        if inspector is None:
            batch.drop_constraint('fk_ai_agent_configs_llm_config_id', type_='foreignkey')
        for fk in foreign_keys:
            batch.drop_constraint(fk['name'] or REFLECTED_FK_NAME, type_='foreignkey')
        batch.drop_column('llm_config_id')

    # 删除 llm_configs 表
    op.drop_table('llm_configs')
