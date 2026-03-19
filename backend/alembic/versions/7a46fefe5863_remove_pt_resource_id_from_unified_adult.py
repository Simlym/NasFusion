"""remove pt_resource_id from unified_adult

Revision ID: 7a46fefe5863
Revises: a1b2c3d4e5f6
Create Date: 2026-02-08 15:12:54.368097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7a46fefe5863'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_unified_adult_pt_resource_id', table_name='unified_adult')
    op.drop_column('unified_adult', 'pt_resource_id')


def downgrade() -> None:
    op.add_column('unified_adult', sa.Column('pt_resource_id', sa.INTEGER(), nullable=True))
    op.create_index('ix_unified_adult_pt_resource_id', 'unified_adult', ['pt_resource_id'], unique=False)
