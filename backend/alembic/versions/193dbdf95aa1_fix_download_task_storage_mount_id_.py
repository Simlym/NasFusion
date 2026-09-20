"""fix download_task storage_mount_id ondelete SET NULL

Revision ID: 193dbdf95aa1
Revises: a9b8c7d6e5f4
Create Date: 2026-03-25 23:19:21.022686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '193dbdf95aa1'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def upgrade() -> None:
    _replace_foreign_key('SET NULL')


def downgrade() -> None:
    _replace_foreign_key()
