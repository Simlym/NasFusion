"""add preset_id to pt_sites

Revision ID: 003
Revises: c618710b817c
Create Date: 2026-01-30 10:00:00.000000

Changes:
- pt_sites: Add preset_id column for site preset configuration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = 'c618710b817c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add preset_id column to pt_sites table
    """
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('pt_sites')]

    if 'preset_id' not in columns:
        op.add_column(
            'pt_sites',
            sa.Column(
                'preset_id',
                sa.String(50),
                nullable=True,
                comment='站点预设ID'
            )
        )
        # Create index for faster lookups
        op.create_index(
            'ix_pt_sites_preset_id',
            'pt_sites',
            ['preset_id'],
            unique=False
        )


def downgrade() -> None:
    """
    Remove preset_id column from pt_sites table
    """
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)

    # Check if column exists before dropping
    columns = [col['name'] for col in inspector.get_columns('pt_sites')]

    if 'preset_id' in columns:
        # Drop index first
        try:
            op.drop_index('ix_pt_sites_preset_id', table_name='pt_sites')
        except Exception:
            pass  # Index might not exist

        op.drop_column('pt_sites', 'preset_id')
