"""add user_profile to pt_sites

Revision ID: 29a741a5bb1c
Revises: 6754bf4afb75
Create Date: 2026-03-21 16:03:21.035221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '29a741a5bb1c'
down_revision: Union[str, None] = '6754bf4afb75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pt_sites', sa.Column('user_profile', sa.JSON(), nullable=True, comment='站点用户信息'))


def downgrade() -> None:
    op.drop_column('pt_sites', 'user_profile')
