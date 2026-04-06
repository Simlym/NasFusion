"""add from_nfo to match_method check constraint

Revision ID: d0f1a2b3c4d5
Revises: b1c2d3e4f5a6
Create Date: 2026-04-05 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0f1a2b3c4d5'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # SQLite 不支持 ALTER constraint，使用 batch mode 重建表
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_constraint('ck_media_file_match_method', type_='check')
        batch_op.create_check_constraint(
            'ck_media_file_match_method',
            "match_method IN ('from_download', 'from_pt_title', 'from_filename', 'from_mediainfo', 'manual', 'from_nfo', 'from_dirname', 'none')"
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_constraint('ck_media_file_match_method', type_='check')
        batch_op.create_check_constraint(
            'ck_media_file_match_method',
            "match_method IN ('from_download', 'from_pt_title', 'from_filename', 'from_mediainfo', 'manual', 'none')"
        )
