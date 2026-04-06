"""add from_dirname to match_method check constraint (merged into d0f1a2b3c4d5)

Revision ID: e2f3a4b5c6d7
Revises: d0f1a2b3c4d5
Create Date: 2026-04-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd0f1a2b3c4d5'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # 已合并到 d0f1a2b3c4d5 迁移中（一起添加了 from_nfo 和 from_dirname）
    pass


def downgrade() -> None:
    pass
