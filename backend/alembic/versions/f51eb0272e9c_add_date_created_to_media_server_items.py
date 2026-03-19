"""add date_created to media_server_items

Revision ID: f51eb0272e9c
Revises: 50497ce09712
Create Date: 2026-03-01 12:04:13.260565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f51eb0272e9c'
down_revision: Union[str, None] = '50497ce09712'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('media_server_items', sa.Column(
        'date_created',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='加入媒体库时间（对应 Jellyfin DateCreated）'
    ))
    op.create_index('ix_media_server_items_date_created', 'media_server_items', ['date_created'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_media_server_items_date_created', table_name='media_server_items')
    op.drop_column('media_server_items', 'date_created')
