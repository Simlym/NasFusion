"""add use_override_for_sync to subscription

Revision ID: c618710b817c
Revises: 002
Create Date: 2026-01-29 21:13:41.474566

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c618710b817c'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 use_override_for_sync 字段到 subscriptions 表
    op.add_column(
        'subscriptions',
        sa.Column(
            'use_override_for_sync',
            sa.Boolean(),
            nullable=False,
            server_default='0',
            comment="是否使用覆写标题进行PT资源同步（解决如'仙逆 年番2'需要用'仙逆'搜索的问题）"
        )
    )


def downgrade() -> None:
    # 删除 use_override_for_sync 字段
    op.drop_column('subscriptions', 'use_override_for_sync')
