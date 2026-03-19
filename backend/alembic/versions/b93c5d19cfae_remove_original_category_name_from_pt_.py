"""remove original_category_name from pt_resources

Revision ID: b93c5d19cfae
Revises: d4e5f6a7b8c9
Create Date: 2026-02-12 22:20:50.539997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b93c5d19cfae'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('pt_resources', 'original_category_name')


def downgrade() -> None:
    op.add_column('pt_resources', sa.Column('original_category_name', sa.VARCHAR(length=200), nullable=True))
