# -*- coding: utf-8 -*-
"""
调度任务服务层
"""
import logging
from datetime import datetime, timedelta
from app.utils.timezone import now
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    LAST_RUN_STATUS_FAILED,
    LAST_RUN_STATUS_RUNNING,
    LAST_RUN_STATUS_SUCCESS,
    RELATED_TYPE_PT_SITE,
    SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL,
    SCHEDULE_TYPE_MANUAL,
    TASK_TYPE_PT_RESOURCE_SYNC,
)
from app.models.scheduled_task import ScheduledTask
from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    PTSyncTaskCreate,
)

logger = logging.getLogger(__name__)


class ScheduledTaskService:
    """调度任务服务"""

    @staticmethod
    async def create(
        db: AsyncSession, task_data: ScheduledTaskCreate
    ) -> ScheduledTask:
        """创建调度任务"""
        # 检查任务名称是否重复
        existing = await ScheduledTaskService.get_by_name(db, task_data.task_name)
        if existing:
            raise ValueError(f"任务名称已存在: {task_data.task_name}")

        task = ScheduledTask(
            task_name=task_data.task_name,
            task_type=task_data.task_type,
            enabled=task_data.enabled,
            schedule_type=task_data.schedule_type,
            schedule_config=task_data.schedule_config,
            handler=task_data.handler,
            handler_params=task_data.handler_params,
            priority=task_data.priority,
            timeout=task_data.timeout,
            max_retries=task_data.max_retries,
            retry_delay=task_data.retry_delay,
            description=task_data.description,
        )

        # 计算下次执行时间
        task.next_run_at = ScheduledTaskService._calculate_next_run(
            task.schedule_type, task.schedule_config
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        logger.info(f"创建调度任务: {task.task_name}, 类型: {task.task_type}")
        return task

    @staticmethod
    async def create_pt_sync_task(
        db: AsyncSession, task_data: PTSyncTaskCreate
    ) -> ScheduledTask:
        """创建PT站点同步任务（快捷方式）"""
        # 设置默认的调度配置
        schedule_config = task_data.schedule_config
        if schedule_config is None:
            if task_data.schedule_type == SCHEDULE_TYPE_INTERVAL:
                # 默认6小时
                schedule_config = {"interval": 21600, "unit": "seconds"}
            elif task_data.schedule_type == SCHEDULE_TYPE_CRON:
                # 默认每天凌晨2点
                schedule_config = {"cron": "0 2 * * *", "timezone": "Asia/Shanghai"}

        # 构建处理器参数
        handler_params = {
            "site_id": task_data.site_id,
            "sync_type": task_data.sync_type,
        }
        if task_data.max_pages:
            handler_params["max_pages"] = task_data.max_pages
        if task_data.request_interval:
            handler_params["request_interval"] = task_data.request_interval

        # 添加过滤参数
        if task_data.mode:
            handler_params["mode"] = task_data.mode
        if task_data.categories:
            handler_params["categories"] = task_data.categories
        if task_data.upload_date_start:
            handler_params["upload_date_start"] = task_data.upload_date_start
        if task_data.upload_date_end:
            handler_params["upload_date_end"] = task_data.upload_date_end
        if task_data.keyword:
            handler_params["keyword"] = task_data.keyword
        if task_data.sortField:
            handler_params["sortField"] = task_data.sortField
        if task_data.sortDirection:
            handler_params["sortDirection"] = task_data.sortDirection

        create_data = ScheduledTaskCreate(
            task_name=task_data.task_name,
            task_type=TASK_TYPE_PT_RESOURCE_SYNC,
            enabled=task_data.enabled,
            schedule_type=task_data.schedule_type,
            schedule_config=schedule_config,
            handler=TASK_TYPE_PT_RESOURCE_SYNC,  # 使用 task_type 作为 handler 标识
            handler_params=handler_params,
            description=task_data.description or f"PT站点同步任务 (站点ID: {task_data.site_id})",
        )

        return await ScheduledTaskService.create(db, create_data)

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: int) -> Optional[ScheduledTask]:
        """根据ID获取任务"""
        result = await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, task_name: str) -> Optional[ScheduledTask]:
        """根据名称获取任务"""
        result = await db.execute(
            select(ScheduledTask).where(ScheduledTask.task_name == task_name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        enabled_only: bool = False,
        task_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[List[ScheduledTask], int]:
        """获取所有任务"""
        query = select(ScheduledTask)

        if enabled_only:
            query = query.where(ScheduledTask.enabled == True)
        if task_type:
            query = query.where(ScheduledTask.task_type == task_type)
        if keyword:
            query = query.where(ScheduledTask.task_name.contains(keyword))

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar()

        # 获取分页数据
        query = query.order_by(ScheduledTask.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total_count

    @staticmethod
    async def update(
        db: AsyncSession, task_id: int, task_data: ScheduledTaskUpdate
    ) -> Optional[ScheduledTask]:
        """更新任务"""
        task = await ScheduledTaskService.get_by_id(db, task_id)
        if not task:
            return None

        update_data = task_data.model_dump(exclude_unset=True)

        # 如果更新了名称，检查是否重复
        if "task_name" in update_data and update_data["task_name"] != task.task_name:
            existing = await ScheduledTaskService.get_by_name(db, update_data["task_name"])
            if existing:
                raise ValueError(f"任务名称已存在: {update_data['task_name']}")

        for field, value in update_data.items():
            setattr(task, field, value)

        # 如果更新了调度配置，重新计算下次执行时间
        if "schedule_type" in update_data or "schedule_config" in update_data:
            task.next_run_at = ScheduledTaskService._calculate_next_run(
                task.schedule_type, task.schedule_config
            )

        await db.commit()
        await db.refresh(task)

        logger.info(f"更新调度任务: {task.task_name}")
        return task

    @staticmethod
    async def delete(db: AsyncSession, task_id: int) -> bool:
        """删除任务"""
        task = await ScheduledTaskService.get_by_id(db, task_id)
        if not task:
            return False

        await db.delete(task)
        await db.commit()

        logger.info(f"删除调度任务: {task.task_name}")
        return True

    @staticmethod
    async def toggle_enabled(db: AsyncSession, task_id: int) -> Optional[ScheduledTask]:
        """切换任务启用状态"""
        task = await ScheduledTaskService.get_by_id(db, task_id)
        if not task:
            return None

        task.enabled = not task.enabled
        if task.enabled:
            # 重新计算下次执行时间
            task.next_run_at = ScheduledTaskService._calculate_next_run(
                task.schedule_type, task.schedule_config
            )
        else:
            task.next_run_at = None

        await db.commit()
        await db.refresh(task)

        logger.info(f"切换任务状态: {task.task_name}, 启用: {task.enabled}")
        return task

    @staticmethod
    async def update_run_status(
        db: AsyncSession,
        task_id: int,
        status: str,
        duration: Optional[int] = None,
    ) -> Optional[ScheduledTask]:
        """更新任务运行状态"""
        task = await ScheduledTaskService.get_by_id(db, task_id)
        if not task:
            return None

        task.last_run_at = now()
        task.last_run_status = status
        task.last_run_duration = duration

        # 只有在任务最终完成（成功或失败）时才增加总运行次数
        # RUNNING 状态只是中间状态，不应该计入统计
        if status in [LAST_RUN_STATUS_SUCCESS, LAST_RUN_STATUS_FAILED]:
            task.total_runs += 1

            if status == LAST_RUN_STATUS_SUCCESS:
                task.success_runs += 1
            elif status == LAST_RUN_STATUS_FAILED:
                task.failed_runs += 1

        # 计算下次执行时间
        if task.enabled and task.schedule_type != SCHEDULE_TYPE_MANUAL:
            task.next_run_at = ScheduledTaskService._calculate_next_run(
                task.schedule_type, task.schedule_config
            )

        await db.commit()
        await db.refresh(task)

        return task

    @staticmethod
    def _calculate_next_run(
        schedule_type: str, schedule_config: Optional[Dict[str, Any]]
    ) -> Optional[datetime]:
        """计算下次执行时间"""
        if schedule_type == SCHEDULE_TYPE_MANUAL:
            return None

        if not schedule_config:
            return None

        current_time = now()

        if schedule_type == SCHEDULE_TYPE_INTERVAL:
            interval = schedule_config.get("interval", 3600)
            unit = schedule_config.get("unit", "seconds")

            if unit == "minutes":
                interval = interval * 60
            elif unit == "hours":
                interval = interval * 3600
            elif unit == "days":
                interval = interval * 86400

            return current_time + timedelta(seconds=interval)

        elif schedule_type == SCHEDULE_TYPE_CRON:
            # 对于cron表达式，返回None，让APScheduler处理
            # 这里简化处理，返回一个小时后
            return current_time + timedelta(hours=1)

        return None

    @staticmethod
    async def get_due_tasks(db: AsyncSession) -> List[ScheduledTask]:
        """获取到期需要执行的任务"""
        current_time = now()
        result = await db.execute(
            select(ScheduledTask).where(
                ScheduledTask.enabled == True,
                ScheduledTask.next_run_at <= current_time,
                ScheduledTask.last_run_status != LAST_RUN_STATUS_RUNNING,
            ).order_by(ScheduledTask.priority.desc(), ScheduledTask.next_run_at)
        )
        return list(result.scalars().all())
