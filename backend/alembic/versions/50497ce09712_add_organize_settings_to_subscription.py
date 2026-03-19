"""add_organize_settings_to_subscription

Revision ID: 50497ce09712
Revises: 51a3d3495948
Create Date: 2026-02-26 23:27:00.226328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '50497ce09712'
down_revision: Union[str, None] = '51a3d3495948'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('auto_organize', sa.Boolean(), nullable=False, server_default=sa.true(),
                  comment='下载完成后是否自动整理（True=整理，False=跳过）')
    )
    op.add_column(
        'subscriptions',
        sa.Column('organize_config_id', sa.Integer(), nullable=True,
                  comment='整理配置ID（空=使用全局默认配置）')
    )
    op.add_column(
        'subscriptions',
        sa.Column('storage_mount_id', sa.Integer(), nullable=True,
                  comment='存储挂载点ID（空=使用全局默认挂载点）')
    )
def downgrade() -> None:
    op.drop_column('subscriptions', 'storage_mount_id')
    op.drop_column('subscriptions', 'organize_config_id')
    op.drop_column('subscriptions', 'auto_organize')
