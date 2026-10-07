"""repair download task storage mount foreign key

Revision ID: 0c7d8e9f1a2b
Revises: f7a8b9c0d1e2
Create Date: 2026-10-07 00:00:00.000000

早期版本曾直接修改已经发布的 193dbdf95aa1 迁移。已经执行过该迁移的
PostgreSQL 数据库不会重新运行它，因此仍可能保留 NO ACTION 外键。本迁移在
当前迁移链末端重新校准约束，确保删除挂载点时下载历史仅清空关联字段。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0c7d8e9f1a2b"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "download_tasks"
COLUMN_NAME = "storage_mount_id"
REFERRED_TABLE = "storage_mounts"
CONSTRAINT_NAME = "fk_download_tasks_storage_mount"


def _storage_mount_foreign_keys(bind):
    return [
        foreign_key
        for foreign_key in sa.inspect(bind).get_foreign_keys(TABLE_NAME)
        if foreign_key.get("constrained_columns") == [COLUMN_NAME]
        and foreign_key.get("referred_table") == REFERRED_TABLE
    ]


def _replace_constraint(ondelete: str | None) -> None:
    bind = op.get_bind()

    # SQLite 生产数据由模型建表，并且删除服务还会显式清空引用。SQLite 不支持
    # 原地修改外键，为单个约束重建整张下载任务表反而会放大迁移风险。
    if bind.dialect.name == "sqlite":
        return

    foreign_keys = _storage_mount_foreign_keys(bind)
    expected_ondelete = ondelete.upper() if ondelete else None
    if len(foreign_keys) == 1:
        current_ondelete = (foreign_keys[0].get("options") or {}).get("ondelete")
        if (current_ondelete or "").upper() == (expected_ondelete or ""):
            return

    for foreign_key in foreign_keys:
        op.drop_constraint(foreign_key["name"], TABLE_NAME, type_="foreignkey")

    op.create_foreign_key(
        CONSTRAINT_NAME,
        TABLE_NAME,
        REFERRED_TABLE,
        [COLUMN_NAME],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    _replace_constraint("SET NULL")


def downgrade() -> None:
    _replace_constraint(None)
