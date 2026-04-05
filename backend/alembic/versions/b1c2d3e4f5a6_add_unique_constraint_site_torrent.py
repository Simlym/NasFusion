"""add unique constraint on (site_id, torrent_id) to pt_resources

Revision ID: b1c2d3e4f5a6
Revises: c7d8e9f0a1b2
Create Date: 2026-04-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pt_resources') as batch_op:
        batch_op.create_unique_constraint('uq_pt_resources_site_torrent', ['site_id', 'torrent_id'])


def downgrade() -> None:
    with op.batch_alter_table('pt_resources') as batch_op:
        batch_op.drop_constraint('uq_pt_resources_site_torrent', type_='unique')
