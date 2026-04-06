"""fix download_task storage_mount_id ondelete SET NULL

Revision ID: 193dbdf95aa1
Revises: a9b8c7d6e5f4
Create Date: 2026-03-25 23:19:21.022686

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '193dbdf95aa1'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('download_tasks_storage_mount_id_fkey', 'download_tasks', type_='foreignkey')
    op.create_foreign_key(None, 'download_tasks', 'storage_mounts', ['storage_mount_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('download_tasks_storage_mount_id_fkey', 'download_tasks', type_='foreignkey')
    op.create_foreign_key(None, 'download_tasks', 'storage_mounts', ['storage_mount_id'], ['id'])
