"""add mcp_external_servers table

Revision ID: a9b8c7d6e5f4
Revises: 29a741a5bb1c
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = '29a741a5bb1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mcp_external_servers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='所有者用户ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Server 名称（用作工具前缀）'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='描述'),
        sa.Column('transport_type', sa.String(length=20), nullable=False, server_default='http', comment='传输类型: http / stdio'),
        sa.Column('url', sa.String(length=500), nullable=True, comment='HTTP SSE 连接 URL'),
        sa.Column('command', sa.String(length=500), nullable=True, comment='stdio 启动命令'),
        sa.Column('command_args', sa.JSON(), nullable=True, comment='stdio 命令参数列表'),
        sa.Column('env_vars', sa.JSON(), nullable=True, comment='环境变量（stdio 用）'),
        sa.Column('auth_type', sa.String(length=20), nullable=False, server_default='none', comment='认证类型: none / bearer / api_key'),
        sa.Column('auth_token', sa.Text(), nullable=True, comment='认证 Token'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1', comment='是否启用'),
        sa.Column('tools_cache', sa.JSON(), nullable=True, comment='工具列表缓存'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True, comment='最后同步时间'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='最后一次错误信息'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mcp_external_servers_id'), 'mcp_external_servers', ['id'], unique=False)
    op.create_index(op.f('ix_mcp_external_servers_user_id'), 'mcp_external_servers', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mcp_external_servers_user_id'), table_name='mcp_external_servers')
    op.drop_index(op.f('ix_mcp_external_servers_id'), table_name='mcp_external_servers')
    op.drop_table('mcp_external_servers')
