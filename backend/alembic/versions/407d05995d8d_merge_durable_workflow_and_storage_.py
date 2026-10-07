"""merge durable workflow and storage mount migrations

Revision ID: 407d05995d8d
Revises: 0c7d8e9f1a2b, ec7094f8e612
Create Date: 2026-10-07 16:46:35.910290

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '407d05995d8d'
down_revision: Union[str, Sequence[str], None] = ('0c7d8e9f1a2b', 'ec7094f8e612')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
