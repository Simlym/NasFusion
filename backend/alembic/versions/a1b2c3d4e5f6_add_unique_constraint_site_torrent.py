"""add unique constraint on (site_id, torrent_id) to pt_resources

Revision ID: a1b2c3d4e5f6
Revises: f51eb0272e9c
Create Date: 2026-04-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f51eb0272e9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_pt_resources_site_torrent', 'pt_resources', ['site_id', 'torrent_id'])


def downgrade() -> None:
    op.drop_constraint('uq_pt_resources_site_torrent', 'pt_resources', type_='unique')
