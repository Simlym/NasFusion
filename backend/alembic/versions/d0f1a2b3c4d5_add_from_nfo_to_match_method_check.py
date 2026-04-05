"""add from_nfo to match_method check constraint

Revision ID: d0f1a2b3c4d5
Revises: c7d8e9f0a1b2
Create Date: 2026-04-05 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd0f1a2b3c4d5'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Drop old constraint and create new one with from_nfo included
    op.drop_constraint('ck_media_file_match_method', 'media_files', type_='check')
    op.create_check_constraint(
        'ck_media_file_match_method',
        'media_files',
        "match_method IN ('from_download', 'from_pt_title', 'from_filename', 'from_mediainfo', 'manual', 'from_nfo', 'none')"
    )


def downgrade() -> None:
    # Revert to old constraint without from_nfo
    op.drop_constraint('ck_media_file_match_method', 'media_files', type_='check')
    op.create_check_constraint(
        'ck_media_file_match_method',
        'media_files',
        "match_method IN ('from_download', 'from_pt_title', 'from_filename', 'from_mediainfo', 'manual', 'none')"
    )
