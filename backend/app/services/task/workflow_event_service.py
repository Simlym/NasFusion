"""下载完成事件的事务 outbox，投递仅创建任务，不执行文件操作。"""
import logging
from datetime import timedelta

from sqlalchemy import String, select, update, func, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.durable_event import (
    DOWNLOAD_ORGANIZE_KEY_PREFIX, EVENT_DELIVERED, EVENT_PENDING,
)
from app.constants.event import EVENT_DOWNLOAD_COMPLETED
from app.constants import TASK_STATUS_DELETED
from app.constants.task import (
    EXECUTION_STATUS_PENDING, TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE, RELATED_TYPE_DOWNLOAD_TASK,
)
from app.models.download_task import DownloadTask
from app.models.task_execution import TaskExecution
from app.models.workflow_event import WorkflowEvent
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class WorkflowEventService:
    @staticmethod
    async def enqueue_download(db: AsyncSession, task: DownloadTask) -> None:
        """与下载完成状态在同一事务写入；调用者提交，重复写入由数据库拒绝。"""
        if not task.auto_organize:
            return
        if db.bind.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        await db.execute(
            insert(WorkflowEvent).values(
                business_key=f"{DOWNLOAD_ORGANIZE_KEY_PREFIX}{task.workflow_token or task.id}",
                event_type=EVENT_DOWNLOAD_COMPLETED,
                payload={
                    "download_task_id": task.id, "save_path": task.save_path,
                    "workflow_token": task.workflow_token,
                },
                status=EVENT_PENDING,
                attempts=0,
            ).on_conflict_do_nothing(index_elements=["business_key"])
        )

    @staticmethod
    async def backfill_completed(db: AsyncSession, limit: int = 100) -> int:
        """修复旧版本或断电前已完成但未投递的下载，每次处理有限数量。"""
        # 关联业务键，而非依赖可以被清理的任务历史。
        result = await db.execute(
            select(DownloadTask).outerjoin(
                WorkflowEvent,
                WorkflowEvent.business_key == DOWNLOAD_ORGANIZE_KEY_PREFIX + func.coalesce(
                    DownloadTask.workflow_token, cast(DownloadTask.id, String),
                ),
            ).where(
                DownloadTask.completed_at.isnot(None),
                DownloadTask.progress == 100,
                DownloadTask.auto_organize.is_(True),
                DownloadTask.status != TASK_STATUS_DELETED,
                WorkflowEvent.id.is_(None),
            ).order_by(DownloadTask.id).limit(limit)
        )
        tasks = result.scalars().all()
        for task in tasks:
            await WorkflowEventService.enqueue_download(db, task)
        await db.commit()
        return len(tasks)

    @staticmethod
    async def deliver(db: AsyncSession, event_id: int) -> None:
        """任务创建和确认投递原子提交；崩溃回滚后仍可重放。"""
        from app.events.handlers.workflow_handler import WORKFLOW_CONFIG
        if not WORKFLOW_CONFIG["download_completed_auto_organize"]["enabled"]:
            return
        # 条件 UPDATE 获取数据库行锁；第二个消费者醒来后不能再次投递。
        claimed = await db.execute(
            update(WorkflowEvent).where(
                WorkflowEvent.id == event_id,
                WorkflowEvent.status == EVENT_PENDING,
            ).values(status=EVENT_DELIVERED)
        )
        if not claimed.rowcount:
            await db.rollback()
            return
        event = await db.get(WorkflowEvent, event_id)
        task_id = event.payload["download_task_id"]
        task = await db.get(DownloadTask, task_id)
        if (task is not None and task.auto_organize and task.status != TASK_STATUS_DELETED
                and task.workflow_token == event.payload.get("workflow_token")):
            # 接管旧版本已创建的整理任务，包括失败/取消记录；不绕过用户取消。
            if db.bind.dialect.name == "postgresql":
                from sqlalchemy.dialects.postgresql import JSONB
                task_id_expression = cast(TaskExecution.handler_params, JSONB)["download_task_id"].astext
                task_id_value = str(task_id)
            else:
                task_id_expression = func.json_extract(TaskExecution.handler_params, "$.download_task_id")
                task_id_value = task_id
            execution = (await db.execute(
                select(TaskExecution).where(
                    TaskExecution.task_type == TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
                    task_id_expression == task_id_value,
                    TaskExecution.created_at >= task.created_at,
                ).order_by(TaskExecution.id.desc()).limit(1)
            )).scalar_one_or_none()
            if execution is None:
                execution = TaskExecution(
                    task_type=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
                    task_name="[自动] 整理下载文件",
                    handler=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
                    handler_params={
                        "download_task_id": task_id, "save_path": task.save_path,
                        "workflow_token": task.workflow_token,
                        "triggered_by": "持久化下载完成事件",
                    },
                    related_type=RELATED_TYPE_DOWNLOAD_TASK, related_id=task_id,
                    status=EXECUTION_STATUS_PENDING, priority=4, max_retries=6,
                    scheduled_at=now(),
                )
                db.add(execution)
                await db.flush()
            event.execution_id = execution.id
        event.delivered_at = now()
        event.last_error = None
        await db.commit()

    @staticmethod
    async def deliver_pending(session_factory, limit: int = 100) -> None:
        async with session_factory() as db:
            ids = (await db.execute(
                select(WorkflowEvent.id).where(
                    WorkflowEvent.status == EVENT_PENDING,
                    (WorkflowEvent.next_attempt_at.is_(None)) | (WorkflowEvent.next_attempt_at <= now()),
                ).order_by(WorkflowEvent.id).limit(limit)
            )).scalars().all()
        for event_id in ids:
            try:
                async with session_factory() as db:
                    await WorkflowEventService.deliver(db, event_id)
            except Exception as exc:
                logger.exception("持久化事件 %s 投递失败，将重试", event_id)
                async with session_factory() as db:
                    event = await db.get(WorkflowEvent, event_id)
                    if event and event.status == EVENT_PENDING:
                        event.attempts += 1
                        event.last_error = str(exc)[:2000]
                        event.next_attempt_at = now() + timedelta(seconds=min(60 * 2 ** min(event.attempts - 1, 6), 3600))
                        await db.commit()
