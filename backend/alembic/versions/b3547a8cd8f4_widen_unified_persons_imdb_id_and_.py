"""widen unified_persons imdb_id and douban_id to varchar 50

Revision ID: b3547a8cd8f4
Revises: 087aa6017ffc
Create Date: 2026-02-12 00:02:27.252235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3547a8cd8f4'
down_revision: Union[str, None] = '087aa6017ffc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('unified_persons') as batch_op:
        batch_op.alter_column('imdb_id',
                   existing_type=sa.String(length=20),
                   type_=sa.String(length=50),
                   existing_nullable=True)
        batch_op.alter_column('douban_id',
                   existing_type=sa.String(length=20),
                   type_=sa.String(length=50),
                   existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('unified_persons') as batch_op:
        batch_op.alter_column('douban_id',
                   existing_type=sa.String(length=50),
                   type_=sa.String(length=20),
                   existing_nullable=True)
        batch_op.alter_column('imdb_id',
                   existing_type=sa.String(length=50),
                   type_=sa.String(length=20),
                   existing_nullable=True)
