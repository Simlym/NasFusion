"""持久化工作流事件：可靠投递、幂等去重与下游任务编排。"""
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from sqlalchemy import String, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TASK_STATUS_DELETED
from app.constants.durable_event import (
    DOWNLOAD_ORGANIZE_KEY_PREFIX, EVENT_DELIVERED, EVENT_PENDING,
    MEDIA_REFRESH_DEBOUNCE_SECONDS, MEDIA_REFRESH_KEY_PREFIX,
    RESOURCE_IDENTIFY_WORKFLOW_KEY_PREFIX, SITE_SYNC_WORKFLOW_KEY_PREFIX,
)
from app.constants.event import (
    EVENT_DOWNLOAD_COMPLETED, EVENT_MEDIA_ORGANIZED,
    EVENT_RESOURCE_IDENTIFIED, EVENT_SITE_SYNC_COMPLETED,
)
from app.constants.task import (
    EXECUTION_STATUS_PENDING, RELATED_TYPE_DOWNLOAD_TASK, RELATED_TYPE_PT_SITE,
    TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE, TASK_TYPE_MEDIA_SERVER_LIBRARY_REFRESH,
    TASK_TYPE_PT_RESOURCE_IDENTIFY, TASK_TYPE_SUBSCRIPTION_CHECK,
)
from app.models.download_task import DownloadTask
from app.models.task_execution import TaskExecution
from app.models.workflow_event import WorkflowEvent
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class WorkflowEventService:
    """将领域事件可靠地转换成可恢复的任务执行记录。"""

    @staticmethod
    async def _enqueue(
        db: AsyncSession, *, business_key: str, event_type: str, payload: Dict[str, Any],
    ) -> None:
        if db.bind.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        await db.execute(
            insert(WorkflowEvent).values(
                business_key=business_key, event_type=event_type, payload=payload,
                status=EVENT_PENDING, attempts=0,
            ).on_conflict_do_nothing(index_elements=["business_key"])
        )

    @staticmethod
    async def enqueue_download(db: AsyncSession, task: DownloadTask) -> None:
        """与下载完成状态在同一事务写入；重复写入由业务键拒绝。"""
        if not task.auto_organize:
            return
        await WorkflowEventService._enqueue(
            db,
            business_key=f"{DOWNLOAD_ORGANIZE_KEY_PREFIX}{task.workflow_token or task.id}",
            event_type=EVENT_DOWNLOAD_COMPLETED,
            payload={
                "download_task_id": task.id, "save_path": task.save_path,
                "workflow_token": task.workflow_token,
            },
        )

    @staticmethod
    async def enqueue_site_sync(db: AsyncSession, event_data: Dict[str, Any]) -> None:
        """持久化一次站点同步结果，作为自动化链路根事件。"""
        sync_log_id = event_data.get("sync_log_id")
        site_id = event_data.get("site_id")
        if not sync_log_id or not site_id:
            raise ValueError("站点同步事件缺少 sync_log_id 或 site_id")
        await WorkflowEventService._enqueue(
            db, business_key=f"{SITE_SYNC_WORKFLOW_KEY_PREFIX}{sync_log_id}",
            event_type=EVENT_SITE_SYNC_COMPLETED, payload=event_data,
        )

    @staticmethod
    async def enqueue_resource_identified(db: AsyncSession, event_data: Dict[str, Any]) -> None:
        """识别结束后可靠触发订阅检查。"""
        execution_id = event_data.get("source_execution_id") or event_data.get("related_id")
        if not execution_id:
            raise ValueError("资源识别事件缺少 source_execution_id")
        await WorkflowEventService._enqueue(
            db, business_key=f"{RESOURCE_IDENTIFY_WORKFLOW_KEY_PREFIX}{execution_id}",
            event_type=EVENT_RESOURCE_IDENTIFIED, payload=event_data,
        )

    @staticmethod
    async def enqueue_media_organized(db: AsyncSession, event_data: Dict[str, Any]) -> None:
        """按用户和时间窗口合并媒体库刷新请求。"""
        user_id = event_data.get("user_id")
        if not user_id:
            raise ValueError("媒体整理事件缺少 user_id")
        bucket = int(now().timestamp()) // MEDIA_REFRESH_DEBOUNCE_SECONDS
        await WorkflowEventService._enqueue(
            db, business_key=f"{MEDIA_REFRESH_KEY_PREFIX}{user_id}:{bucket}",
            event_type=EVENT_MEDIA_ORGANIZED, payload=event_data,
        )

    @staticmethod
    async def backfill_completed(db: AsyncSession, limit: int = 100) -> int:
        """修复旧版本或断电前已完成但未投递的下载。"""
        result = await db.execute(
            select(DownloadTask).outerjoin(
                WorkflowEvent,
                WorkflowEvent.business_key == DOWNLOAD_ORGANIZE_KEY_PREFIX + func.coalesce(
                    DownloadTask.workflow_token, cast(DownloadTask.id, String),
                ),
            ).where(
                DownloadTask.completed_at.isnot(None), DownloadTask.progress == 100,
                DownloadTask.auto_organize.is_(True), DownloadTask.status != TASK_STATUS_DELETED,
                WorkflowEvent.id.is_(None),
            ).order_by(DownloadTask.id).limit(limit)
        )
        tasks = result.scalars().all()
        for task in tasks:
            await WorkflowEventService.enqueue_download(db, task)
        await db.commit()
        return len(tasks)

    @staticmethod
    async def _find_pending_execution(
        db: AsyncSession, task_type: str, *,
        related_type: Optional[str] = None, related_id: Optional[int] = None,
    ) -> Optional[TaskExecution]:
        query = select(TaskExecution).where(
            TaskExecution.task_type == task_type,
            TaskExecution.status == EXECUTION_STATUS_PENDING,
        )
        if related_type is not None:
            query = query.where(TaskExecution.related_type == related_type)
        if related_id is not None:
            query = query.where(TaskExecution.related_id == related_id)
        return (await db.execute(query.order_by(TaskExecution.id).limit(1))).scalar_one_or_none()

    @staticmethod
    def _merge_workflow_ids(execution: TaskExecution, workflow_run_id: str) -> None:
        metadata = dict(execution.task_metadata or {})
        workflow_ids = list(metadata.get("workflow_run_ids") or [])
        if workflow_run_id not in workflow_ids:
            workflow_ids.append(workflow_run_id)
        metadata.update({"workflow_run_ids": workflow_ids, "trigger_source": "workflow"})
        execution.task_metadata = metadata
        params = dict(execution.handler_params or {})
        params["workflow_run_ids"] = workflow_ids
        execution.handler_params = params

    @staticmethod
    async def _create_subscription_execution(
        db: AsyncSession, *, workflow_run_id: str, triggered_by: str,
    ) -> TaskExecution:
        pending = await WorkflowEventService._find_pending_execution(db, TASK_TYPE_SUBSCRIPTION_CHECK)
        if pending:
            WorkflowEventService._merge_workflow_ids(pending, workflow_run_id)
            return pending
        execution = TaskExecution(
            task_type=TASK_TYPE_SUBSCRIPTION_CHECK, task_name="[自动] 检查订阅",
            handler=TASK_TYPE_SUBSCRIPTION_CHECK,
            handler_params={
                "check_all": True, "triggered_by": triggered_by,
                "workflow_run_ids": [workflow_run_id],
            },
            task_metadata={
                "workflow_run_ids": [workflow_run_id], "workflow_step": "subscription_check",
                "trigger_source": "workflow",
            },
            status=EXECUTION_STATUS_PENDING, priority=2, max_retries=3, scheduled_at=now(),
        )
        db.add(execution)
        await db.flush()
        return execution

    @staticmethod
    async def _deliver_site_sync(db: AsyncSession, event: WorkflowEvent) -> Optional[TaskExecution]:
        from app.events.handlers.workflow_handler import WORKFLOW_CONFIG
        from app.services.pt.pt_resource_service import PTResourceService

        payload = event.payload
        site_id = payload["site_id"]
        site_name = payload.get("site_name", f"站点{site_id}")
        workflow_run_id = event.business_key
        if (WORKFLOW_CONFIG["site_sync_auto_identify"]["enabled"]
                and payload.get("resources_new", 0) > 0):
            resources = await PTResourceService.get_unidentified_resources(
                db, site_id=site_id,
                limit=WORKFLOW_CONFIG["site_sync_auto_identify"]["max_resources"],
            )
            if resources:
                pending = await WorkflowEventService._find_pending_execution(
                    db, TASK_TYPE_PT_RESOURCE_IDENTIFY,
                    related_type=RELATED_TYPE_PT_SITE, related_id=site_id,
                )
                resource_ids = [resource.id for resource in resources]
                if pending:
                    params = dict(pending.handler_params or {})
                    params["pt_resource_ids"] = sorted(
                        set(params.get("pt_resource_ids", [])) | set(resource_ids)
                    )
                    pending.handler_params = params
                    WorkflowEventService._merge_workflow_ids(pending, workflow_run_id)
                    return pending
                execution = TaskExecution(
                    task_type=TASK_TYPE_PT_RESOURCE_IDENTIFY,
                    task_name=f"[自动] 识别 {site_name} 新资源",
                    handler=TASK_TYPE_PT_RESOURCE_IDENTIFY,
                    handler_params={
                        "pt_resource_ids": resource_ids, "site_id": site_id,
                        "media_type": "auto",
                        "skip_errors": WORKFLOW_CONFIG["site_sync_auto_identify"]["skip_errors"],
                        "triggered_by": f"站点同步完成: {site_name}",
                        "workflow_run_ids": [workflow_run_id],
                    },
                    task_metadata={
                        "workflow_run_ids": [workflow_run_id], "workflow_step": "resource_identify",
                        "trigger_source": "workflow",
                    },
                    related_type=RELATED_TYPE_PT_SITE, related_id=site_id,
                    status=EXECUTION_STATUS_PENDING,
                    priority=WORKFLOW_CONFIG["site_sync_auto_identify"]["priority"],
                    max_retries=3, scheduled_at=now(),
                )
                db.add(execution)
                await db.flush()
                return execution
        if WORKFLOW_CONFIG["site_sync_auto_check_subscription"]["enabled"]:
            return await WorkflowEventService._create_subscription_execution(
                db, workflow_run_id=workflow_run_id,
                triggered_by=f"站点同步完成: {site_name}",
            )
        return None

    @staticmethod
    async def _deliver_resource_identified(
        db: AsyncSession, event: WorkflowEvent,
    ) -> Optional[TaskExecution]:
        from app.events.handlers.workflow_handler import WORKFLOW_CONFIG
        if not WORKFLOW_CONFIG["site_sync_auto_check_subscription"]["enabled"]:
            return None
        workflow_ids = event.payload.get("workflow_run_ids") or [event.business_key]
        execution = None
        for workflow_run_id in workflow_ids:
            execution = await WorkflowEventService._create_subscription_execution(
                db, workflow_run_id=workflow_run_id, triggered_by="资源识别完成",
            )
        return execution

    @staticmethod
    async def _deliver_download(db: AsyncSession, event: WorkflowEvent) -> Optional[TaskExecution]:
        from app.events.handlers.workflow_handler import WORKFLOW_CONFIG
        if not WORKFLOW_CONFIG["download_completed_auto_organize"]["enabled"]:
            return None
        task_id = event.payload["download_task_id"]
        task = await db.get(DownloadTask, task_id)
        if (task is None or not task.auto_organize or task.status == TASK_STATUS_DELETED
                or task.workflow_token != event.payload.get("workflow_token")):
            return None
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
                task_name="[自动] 整理下载文件", handler=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
                handler_params={
                    "download_task_id": task_id, "workflow_token": task.workflow_token,
                    "triggered_by": "持久化下载完成事件",
                },
                task_metadata={"workflow_step": "media_organize", "trigger_source": "workflow"},
                related_type=RELATED_TYPE_DOWNLOAD_TASK, related_id=task_id,
                status=EXECUTION_STATUS_PENDING, priority=4, max_retries=6, scheduled_at=now(),
            )
            db.add(execution)
            await db.flush()
        return execution

    @staticmethod
    async def _deliver_media_organized(
        db: AsyncSession, event: WorkflowEvent,
    ) -> Optional[TaskExecution]:
        user_id = event.payload.get("user_id")
        pending_executions = (await db.execute(
            select(TaskExecution).where(
                TaskExecution.task_type == TASK_TYPE_MEDIA_SERVER_LIBRARY_REFRESH,
                TaskExecution.status == EXECUTION_STATUS_PENDING,
            ).order_by(TaskExecution.id)
        )).scalars().all()
        pending = next(
            (
                execution for execution in pending_executions
                if (execution.handler_params or {}).get("user_id") == user_id
            ),
            None,
        )
        if pending:
            params = dict(pending.handler_params or {})
            params["organized_count"] = (
                params.get("organized_count", 0) + event.payload.get("organized_count", 0)
            )
            pending.handler_params = params
            return pending
        execution = TaskExecution(
            task_type=TASK_TYPE_MEDIA_SERVER_LIBRARY_REFRESH,
            task_name="[自动] 刷新媒体服务器媒体库",
            handler=TASK_TYPE_MEDIA_SERVER_LIBRARY_REFRESH,
            handler_params={
                "user_id": user_id, "organized_count": event.payload.get("organized_count", 0),
                "triggered_by": "媒体文件整理完成",
            },
            task_metadata={"workflow_step": "media_library_refresh", "trigger_source": "workflow"},
            status=EXECUTION_STATUS_PENDING, priority=3, max_retries=3,
            scheduled_at=now() + timedelta(seconds=MEDIA_REFRESH_DEBOUNCE_SECONDS),
        )
        db.add(execution)
        await db.flush()
        return execution

    @staticmethod
    async def deliver(db: AsyncSession, event_id: int) -> None:
        """任务创建和确认投递原子提交；崩溃回滚后仍可重放。"""
        claimed = await db.execute(
            update(WorkflowEvent).where(
                WorkflowEvent.id == event_id, WorkflowEvent.status == EVENT_PENDING,
            ).values(status=EVENT_DELIVERED)
        )
        if not claimed.rowcount:
            await db.rollback()
            return
        event = await db.get(WorkflowEvent, event_id)
        if event.event_type == EVENT_DOWNLOAD_COMPLETED:
            execution = await WorkflowEventService._deliver_download(db, event)
        elif event.event_type == EVENT_SITE_SYNC_COMPLETED:
            execution = await WorkflowEventService._deliver_site_sync(db, event)
        elif event.event_type == EVENT_RESOURCE_IDENTIFIED:
            execution = await WorkflowEventService._deliver_resource_identified(db, event)
        elif event.event_type == EVENT_MEDIA_ORGANIZED:
            execution = await WorkflowEventService._deliver_media_organized(db, event)
        else:
            raise ValueError(f"不支持的持久化工作流事件: {event.event_type}")
        if execution is not None:
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
                        event.next_attempt_at = now() + timedelta(
                            seconds=min(60 * 2 ** min(event.attempts - 1, 6), 3600)
                        )
                        await db.commit()
