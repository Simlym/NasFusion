"""验证人工确认与失败结果分离、跨会话持久化及新失败重新提醒。"""
from datetime import timedelta
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, ScheduledTask, TaskExecution
from app.core.config import settings
from app.schemas.task_execution import TaskAttentionRequest, TaskExecutionResponse
from app.services.task.task_attention_service import (
    AttentionConflict,
    TaskAttentionService,
)
from app.services.task.task_execution_service import TaskExecutionService
from app.services.task.scheduled_task_service import ScheduledTaskService
from app.utils.timezone import now


@pytest_asyncio.fixture
async def sessions(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'attention.db').as_posix()}"
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def seed(db, status="failed", scheduled=True, age=0):
    completed_at = now() - timedelta(hours=age)
    task = None
    if scheduled:
        task = ScheduledTask(
            task_name="sync",
            task_type="pt_resource_sync",
            handler="sync",
            schedule_type="manual",
            last_run_status="failed",
            last_run_at=completed_at + timedelta(milliseconds=1),
            total_runs=1,
            failed_runs=1,
        )
        db.add(task)
        await db.flush()
    execution = TaskExecution(
        task_name="sync execution",
        task_type="pt_resource_sync",
        handler="sync",
        scheduled_task_id=task.id if task else None,
        status=status,
        completed_at=completed_at,
        error_message="keep original error",
        logs="keep log",
    )
    db.add(execution)
    await db.commit()
    return task, execution


@pytest.mark.parametrize("attention_status", ["resolved", "ignored"])
async def test_handling_persists_preserves_failure_and_does_not_resurface_as_schedule(
    sessions, attention_status
):
    async with sessions() as db:
        task, execution = await seed(db)
        task_id, execution_id = task.id, execution.id
        await TaskAttentionService.set_execution(db, execution_id, attention_status, 42)
    async with sessions() as db:
        execution = await db.get(TaskExecution, execution_id)
        task = await db.get(ScheduledTask, task_id)
        assert execution.status == "failed"
        assert execution.error_message == "keep original error"
        assert execution.logs == "keep log"
        assert execution.attention_status == attention_status
        assert execution.attention_handled_by == 42
        assert execution.attention_handled_at is not None
        assert task.attention_run_at == task.last_run_at
        assert task.attention_status == attention_status
        assert task.failed_runs == task.total_runs == 1
        serialized = TaskExecutionResponse.model_validate(execution).model_dump(
            mode="json"
        )
        assert serialized["attention_handled_at"].endswith("+08:00")
        await TaskAttentionService.set_execution(db, execution_id, "pending", 42)
        await db.refresh(task)
        assert execution.attention_status is None
        assert execution.attention_handled_at is None
        assert task.attention_run_at is None


async def test_new_failure_is_not_acknowledged_and_old_resolution_does_not_hide_it(
    sessions,
):
    async with sessions() as db:
        task, old = await seed(db)
        await TaskAttentionService.set_execution(db, old.id, "resolved", 1)
        acknowledged_run = task.last_run_at
        await ScheduledTaskService.update_run_status(db, task.id, "running")
        new = TaskExecution(
            task_name="new",
            task_type="pt_resource_sync",
            handler="sync",
            scheduled_task_id=task.id,
            status="failed",
            completed_at=now(),
        )
        db.add(new)
        await db.commit()
        await ScheduledTaskService.update_run_status(db, task.id, "failed")
        assert task.last_run_at != task.attention_run_at
        assert new.attention_status is None
        with pytest.raises(AttentionConflict):
            await TaskAttentionService.set_scheduled(
                db, task.id, "ignored", 1, acknowledged_run
            )
        await TaskAttentionService.set_execution(db, old.id, "ignored", 1)
        await db.refresh(task)
        assert task.attention_run_at == acknowledged_run
        assert task.attention_run_at != task.last_run_at
        await TaskAttentionService.set_execution(db, old.id, "pending", 1)
        await db.refresh(new)
        assert new.attention_status is None


async def test_old_scheduled_failure_can_be_handled_and_restored(sessions):
    async with sessions() as db:
        task, execution = await seed(db, age=48)
        assert not (await TaskExecutionService.get_queue_status(db))["recent_completed"]
        run_at = task.last_run_at
        await TaskAttentionService.set_scheduled(db, task.id, "ignored", 7, run_at)
        await db.refresh(execution)
        assert execution.attention_status == "ignored"
        assert task.attention_run_at == run_at
        await TaskAttentionService.set_scheduled(db, task.id, "pending", 7, run_at)
        await db.refresh(execution)
        assert execution.attention_status is None
        assert task.attention_status is None


async def test_scheduled_failure_without_execution(sessions):
    async with sessions() as db:
        task, execution = await seed(db)
        await db.delete(execution)
        await db.commit()
        await TaskAttentionService.set_scheduled(
            db, task.id, "resolved", 1, task.last_run_at
        )
        assert task.attention_status == "resolved"
        assert task.attention_run_at == task.last_run_at


async def test_legacy_scheduled_failure_without_run_timestamp(sessions):
    async with sessions() as db:
        task, execution = await seed(db)
        await db.delete(execution)
        task.last_run_at = None
        await db.commit()
        await TaskAttentionService.set_scheduled(db, task.id, "ignored", 1, None)
        assert task.attention_status == "ignored"
        await ScheduledTaskService.update_run_status(db, task.id, "failed")
        assert task.last_run_at is not None
        assert task.attention_run_at != task.last_run_at


async def test_timeout_is_visible_and_handleable(sessions):
    async with sessions() as db:
        _, execution = await seed(db, status="timeout", scheduled=False)
        queue = await TaskExecutionService.get_queue_status(db)
        assert queue["recent_completed"][0].id == execution.id
        await TaskAttentionService.set_execution(db, execution.id, "ignored", 1)
        assert execution.status == "timeout"
        assert execution.attention_status == "ignored"


@pytest.mark.parametrize("status", ["pending", "running", "completed", "cancelled"])
async def test_non_failure_cannot_be_handled(sessions, status):
    async with sessions() as db:
        _, execution = await seed(db, status=status, scheduled=False)
        with pytest.raises(ValueError, match="只有失败"):
            await TaskAttentionService.set_execution(db, execution.id, "resolved", 1)


async def test_missing_targets_and_invalid_status(sessions):
    async with sessions() as db:
        assert await TaskAttentionService.set_execution(db, 999, "resolved", 1) is None
        assert (
            await TaskAttentionService.set_scheduled(db, 999, "resolved", 1, None)
            is None
        )
        with pytest.raises(ValueError):
            TaskAttentionRequest(attention_status="completed")


async def test_handling_schedule_does_not_change_newer_execution(sessions):
    async with sessions() as db:
        task, old = await seed(db)
        # 新失败已经落库，但调度器尚未更新 last_run_at。
        new = TaskExecution(
            task_name="new",
            task_type="pt_resource_sync",
            handler="sync",
            scheduled_task_id=task.id,
            status="failed",
            completed_at=now(),
        )
        db.add(new)
        await db.commit()
        await TaskAttentionService.set_scheduled(
            db, task.id, "resolved", 1, task.last_run_at
        )
        await db.refresh(new)
        assert new.attention_status is None
        await TaskAttentionService.set_execution(db, new.id, "ignored", 1)
        await db.refresh(task)
        await ScheduledTaskService.update_run_status(db, task.id, "failed")
        assert task.attention_run_at != task.last_run_at


def test_attention_migration_and_rollback_preserve_existing_failures(
    tmp_path, monkeypatch
):
    path = tmp_path / "migration.db"
    monkeypatch.setattr(settings.database, "DB_TYPE", "sqlite")
    monkeypatch.setattr(settings.database, "SQLITE_PATH", path.as_posix())
    engine = sa.create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE task_executions (id INTEGER PRIMARY KEY, status TEXT, error_message TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE scheduled_tasks (id INTEGER PRIMARY KEY, last_run_status TEXT, total_runs INTEGER)"
        )
        conn.exec_driver_sql(
            "INSERT INTO task_executions VALUES (1, 'failed', 'original failure')"
        )
        conn.exec_driver_sql("INSERT INTO scheduled_tasks VALUES (1, 'failed', 3)")
    backend = Path(__file__).resolve().parents[3]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    command.stamp(config, "407d05995d8d")
    command.upgrade(config, "head")
    with engine.begin() as conn:
        assert (
            conn.exec_driver_sql(
                "SELECT attention_status FROM task_executions"
            ).scalar()
            is None
        )
        assert (
            conn.exec_driver_sql(
                "SELECT attention_run_at FROM scheduled_tasks"
            ).scalar()
            is None
        )
        conn.exec_driver_sql(
            "UPDATE task_executions SET attention_status='resolved', attention_handled_by=1"
        )
        assert conn.exec_driver_sql(
            "SELECT status, error_message FROM task_executions"
        ).one() == ("failed", "original failure")
        assert conn.exec_driver_sql(
            "SELECT last_run_status, total_runs FROM scheduled_tasks"
        ).one() == ("failed", 3)
    command.downgrade(config, "407d05995d8d")
    with engine.connect() as conn:
        assert conn.exec_driver_sql(
            "SELECT status, error_message FROM task_executions"
        ).one() == ("failed", "original failure")
        assert "attention_status" not in {
            column["name"] for column in sa.inspect(conn).get_columns("task_executions")
        }
    engine.dispose()
