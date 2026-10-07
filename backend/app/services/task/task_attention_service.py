"""人工确认失败提醒；保留执行结果，不影响任务调度和重试。"""
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_task import ScheduledTask
from app.models.task_execution import TaskExecution
from app.utils.timezone import now


class AttentionConflict(ValueError):
    """页面展示的运行已被新的运行取代。"""


class TaskAttentionService:
    @staticmethod
    def _values(attention_status: str, user_id: int) -> dict:
        if attention_status not in ("pending", "resolved", "ignored"):
            raise ValueError("无效的提醒处理状态")
        return {
            "attention_status": None
            if attention_status == "pending"
            else attention_status,
            "attention_handled_at": None if attention_status == "pending" else now(),
            "attention_handled_by": None if attention_status == "pending" else user_id,
        }

    @staticmethod
    async def _latest_execution(db: AsyncSession, task_id: int):
        # 包含进行中的记录，避免确认旧失败时误确认新的执行。
        return await db.scalar(
            select(TaskExecution)
            .where(TaskExecution.scheduled_task_id == task_id)
            .order_by(TaskExecution.created_at.desc(), TaskExecution.id.desc())
            .limit(1)
        )

    @staticmethod
    async def set_execution(
        db: AsyncSession, execution_id: int, attention_status: str, user_id: int
    ):
        values = TaskAttentionService._values(attention_status, user_id)
        execution = await db.get(TaskExecution, execution_id)
        if execution is None:
            return None
        if execution.status not in ("failed", "timeout"):
            raise ValueError("只有失败或超时的执行记录可以处理提醒")
        result = await db.execute(
            update(TaskExecution)
            .where(
                TaskExecution.id == execution_id,
                TaskExecution.status.in_(["failed", "timeout"]),
            )
            .values(**values)
        )
        if not result.rowcount:
            raise AttentionConflict("执行状态已变化，请刷新后重试")

        if execution.scheduled_task_id:
            task = await db.get(ScheduledTask, execution.scheduled_task_id)
            latest = await TaskAttentionService._latest_execution(
                db, execution.scheduled_task_id
            )
            if (
                task is not None
                and task.last_run_status == "failed"
                and latest is not None
                and latest.id == execution_id
                and execution.completed_at is not None
                and task.last_run_at is not None
                and execution.completed_at <= task.last_run_at
            ):
                # 用运行时间作条件更新，即使调度器并发启动新运行也不会屏蔽新提醒。
                await db.execute(
                    update(ScheduledTask)
                    .where(
                        ScheduledTask.id == task.id,
                        ScheduledTask.last_run_at == task.last_run_at,
                        ScheduledTask.last_run_status == "failed",
                    )
                    .values(
                        **values,
                        attention_run_at=None
                        if attention_status == "pending"
                        else task.last_run_at,
                    )
                )
        await db.commit()
        await db.refresh(execution)
        return execution

    @staticmethod
    async def set_scheduled(
        db: AsyncSession,
        task_id: int,
        attention_status: str,
        user_id: int,
        last_run_at: datetime | None,
    ):
        values = TaskAttentionService._values(attention_status, user_id)
        task = await db.get(ScheduledTask, task_id)
        if task is None:
            return None
        if task.last_run_status != "failed" or task.last_run_at != last_run_at:
            raise AttentionConflict("任务已再次运行，请刷新后处理当前提醒")
        result = await db.execute(
            update(ScheduledTask)
            .where(
                ScheduledTask.id == task_id,
                ScheduledTask.last_run_status == "failed",
                ScheduledTask.last_run_at == last_run_at,
            )
            .values(
                **values,
                attention_run_at=None if attention_status == "pending" else last_run_at,
            )
        )
        if not result.rowcount:
            raise AttentionConflict("任务已再次运行，请刷新后处理当前提醒")
        latest = await TaskAttentionService._latest_execution(db, task_id)
        if (
            latest is not None
            and latest.status in ("failed", "timeout")
            and latest.completed_at is not None
            and last_run_at is not None
            and latest.completed_at <= last_run_at
        ):
            await db.execute(
                update(TaskExecution)
                .where(
                    TaskExecution.id == latest.id,
                    TaskExecution.status.in_(["failed", "timeout"]),
                )
                .values(**values)
            )
        await db.commit()
        await db.refresh(task)
        return task
