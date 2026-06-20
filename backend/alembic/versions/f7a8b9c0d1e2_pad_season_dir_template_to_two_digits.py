"""pad season dir template to two digits (Season 1 -> Season 01)

Revision ID: f7a8b9c0d1e2
Revises: e2f3a4b5c6d7
Create Date: 2026-06-20 12:00:00.000000

将已有 organize_configs 的目录模板中未补零的 `Season {season}` 升级为
`Season {season:02d}`，避免 Jellyfin/Emby 把剧集误判到「未知季」。

仅替换精确子串 `Season {season}`，不影响用户自定义的其它模板。
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE organize_configs "
        "SET dir_template = REPLACE(dir_template, 'Season {season}', 'Season {season:02d}') "
        "WHERE dir_template LIKE '%Season {season}%'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE organize_configs "
        "SET dir_template = REPLACE(dir_template, 'Season {season:02d}', 'Season {season}') "
        "WHERE dir_template LIKE '%Season {season:02d}%'"
    )
