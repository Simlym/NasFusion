"""Persist manual handling of task failures without changing execution results."""
from alembic import op
import sqlalchemy as sa

from app.core.db_types import TZDateTime

revision = "4a8b9c0d1e2f"
down_revision = "407d05995d8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some legacy installations have no scheduled_tasks table yet.
    tables = sa.inspect(op.get_bind()).get_table_names()
    for table in ("task_executions", "scheduled_tasks"):
        if table not in tables:
            continue
        op.add_column(
            table, sa.Column("attention_status", sa.String(20), nullable=True)
        )
        op.add_column(
            table, sa.Column("attention_handled_at", TZDateTime(), nullable=True)
        )
        op.add_column(
            table, sa.Column("attention_handled_by", sa.Integer(), nullable=True)
        )
        if table == "scheduled_tasks":
            op.add_column(
                table, sa.Column("attention_run_at", TZDateTime(), nullable=True)
            )


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    for table in ("scheduled_tasks", "task_executions"):
        if table not in tables:
            continue
        with op.batch_alter_table(table) as batch:
            if table == "scheduled_tasks":
                batch.drop_column("attention_run_at")
            batch.drop_column("attention_handled_by")
            batch.drop_column("attention_handled_at")
            batch.drop_column("attention_status")
