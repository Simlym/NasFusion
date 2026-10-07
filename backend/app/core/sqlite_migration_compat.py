"""SQLite compatibility for released migrations without changing revision files."""
from alembic import op
import sqlalchemy as sa

def _replace_foreign_key(ondelete=None) -> None:
    name = 'fk_download_tasks_storage_mount'
    if op.get_bind().dialect.name != 'sqlite':
        op.drop_constraint(name, 'download_tasks', type_='foreignkey')
        op.create_foreign_key(name, 'download_tasks', 'storage_mounts', ['storage_mount_id'], ['id'], ondelete=ondelete)
        return

    # create_all 创建的外键可能没有名称，反射时给它分配一个可供 batch 删除的名字。
    foreign_keys = [fk for fk in sa.inspect(op.get_bind()).get_foreign_keys('download_tasks')
                    if fk['constrained_columns'] == ['storage_mount_id']]
    for fk in foreign_keys:
        if fk['referred_table'] != 'storage_mounts' or fk['referred_columns'] != ['id']:
            raise RuntimeError('download_tasks.storage_mount_id 的外键目标不匹配')
    if len(foreign_keys) == 1 and foreign_keys[0].get('options', {}).get('ondelete') == ondelete:
        return
    with op.batch_alter_table('download_tasks', naming_convention={
        'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    }) as batch:
        for fk in foreign_keys:
            batch.drop_constraint(fk['name'] or 'fk_download_tasks_storage_mount_id_storage_mounts', type_='foreignkey')
        batch.create_foreign_key(name, 'storage_mounts', ['storage_mount_id'], ['id'], ondelete=ondelete)


def upgrade_download_mount() -> None:
    _replace_foreign_key('SET NULL')


def downgrade_download_mount() -> None:
    _replace_foreign_key()

def upgrade_llm_config() -> None:
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


def downgrade_llm_config() -> None:
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

def compatible_steps(original_fn):
    """Keep Alembic's revision graph and replace only SQLite operation callbacks."""
    handlers = {
        "193dbdf95aa1": (upgrade_download_mount, downgrade_download_mount),
        "c7d8e9f0a1b2": (upgrade_llm_config, downgrade_llm_config),
    }

    def steps(heads, migration_context):
        for step in original_fn(heads, migration_context):
            revision = getattr(getattr(step, "revision", None), "revision", None)
            if revision in handlers:
                step.migration_fn = handlers[revision][0 if step.is_upgrade else 1]
            yield step

    return steps
