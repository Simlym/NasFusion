"""initial schema baseline

Revision ID: 001
Revises:
Create Date: 2026-01-24 11:00:00.000000

This migration marks the initial database state.
All tables already exist, so this is just a baseline marker.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline migration - no changes needed
    # All tables already exist in the database
    pass


def downgrade() -> None:
    # Cannot downgrade from baseline
    pass
