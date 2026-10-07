"""identify download workflow generations

Revision ID: ec7094f8e612
Revises: 5bb170d6737e
Create Date: 2026-09-21 06:38:57.858907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec7094f8e612'
down_revision: Union[str, None] = '5bb170d6737e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('download_tasks', sa.Column('workflow_token', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('download_tasks', 'workflow_token')
