"""add login_history table

Revision ID: d4e5f6a7b8c9
Revises: b3547a8cd8f4
Create Date: 2026-02-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b3547a8cd8f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'login_histories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='登录IP地址（支持IPv6）'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='浏览器User-Agent'),
        sa.Column('location', sa.String(length=255), nullable=True, comment='IP所在地（国家/省/市）'),
        sa.Column('login_status', sa.String(length=20), nullable=False, server_default='success', comment='登录状态: success/failed/locked'),
        sa.Column('failure_reason', sa.String(length=100), nullable=True, comment='失败原因'),
        sa.Column('login_at', sa.DateTime(timezone=True), nullable=False, comment='登录时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_login_histories_id'), 'login_histories', ['id'], unique=False)
    op.create_index(op.f('ix_login_histories_user_id'), 'login_histories', ['user_id'], unique=False)
    op.create_index(op.f('ix_login_histories_login_at'), 'login_histories', ['login_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_login_histories_login_at'), table_name='login_histories')
    op.drop_index(op.f('ix_login_histories_user_id'), table_name='login_histories')
    op.drop_index(op.f('ix_login_histories_id'), table_name='login_histories')
    op.drop_table('login_histories')
