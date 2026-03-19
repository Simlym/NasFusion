# -*- coding: utf-8 -*-
"""
任务调度器管理器
使用APScheduler管理定时任务
"""
import asyncio
import logging
from datetime import datetime
from app.utils.timezone import now
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    EXECUTION_STATUS_PENDING,
    LAST_RUN_STATUS_FAILED,
    LAST_RUN_STATUS_RUNNING,
    LAST_RUN_STATUS_SUCCESS,
    RELATED_TYPE_PT_SITE,
    RELATED_TYPE_SUBSCRIPTION,
    SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL,
    SCHEDULE_TYPE_MANUAL,
    TASK_TYPE_PT_RESOURCE_IDENTIFY,
    TASK_TYPE_TASK_EXECUTION_CLEANUP,
    TASK_TYPE_DOWNLOAD_CREATE,
    TASK_TYPE_PT_RESOURCE_SYNC,
    TASK_TYPE_MEDIA_FILE_SCAN,
    TASK_TYPE_SUBSCRIPTION_CHECK,
    TASK_TYPE_DOWNLOAD_STATUS_SYNC,
)
from app.core.database import async_session_local
from app.models.scheduled_task import ScheduledTask
from app.schemas.task_execution import TaskExecutionCreate
from app.services.task.scheduled_task_service import ScheduledTaskService
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class SchedulerManager:
    """调度器管理器"""

    _instance: Optional["SchedulerManager"] = None
    _scheduler: Optional[AsyncIOScheduler] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._scheduler = AsyncIOScheduler()
            self._initialized = True

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """获取调度器实例"""
        return self._scheduler

    async def start(self):
        """启动调度器"""
        if self._scheduler.running:
            logger.warning("调度器已在运行中")
            return

        # 注册所有任务处理器
        from app.tasks.registry import register_all_handlers
        register_all_handlers()

        # 加载所有已启用的任务
        await self._load_scheduled_tasks()

        # 启动调度器
        self._scheduler.start()
        logger.info("任务调度器已启动")

    async def shutdown(self):
        """关闭调度器"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("任务调度器已关闭")

    async def _load_scheduled_tasks(self):
        """从数据库加载所有已启用的任务"""
        async with async_session_local() as db:
            tasks, _ = await ScheduledTaskService.get_all(db, limit=1000, enabled_only=True)

            for task in tasks:
                await self.add_job(task)

            logger.debug(f"已加载 {len(tasks)} 个调度任务")

    async def add_job(self, task: ScheduledTask):
        """添加任务到调度器"""
        job_id = f"task_{task.id}"

        # 如果任务已存在，先移除
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        if task.schedule_type == SCHEDULE_TYPE_MANUAL:
            # 手动任务不添加到调度器
            logger.debug(f"跳过手动任务: {task.task_name}")
            return

        # 根据调度类型创建触发器
        trigger = self._create_trigger(task)
        if not trigger:
            logger.warning(f"无法为任务 {task.task_name} 创建触发器")
            return

        # 添加任务
        self._scheduler.add_job(
            func=self._execute_scheduled_task,
            trigger=trigger,
            args=[task.id],
            id=job_id,
            name=task.task_name,
            replace_existing=True,
        )

        logger.debug(f"已添加调度任务: {task.task_name} (ID: {task.id})")

    def _create_trigger(self, task: ScheduledTask):
        """创建APScheduler触发器"""
        config = task.schedule_config or {}

        if task.schedule_type == SCHEDULE_TYPE_INTERVAL:
            interval = config.get("interval", 3600)
            unit = config.get("unit", "seconds")

            if unit == "minutes":
                return IntervalTrigger(minutes=interval)
            elif unit == "hours":
                return IntervalTrigger(hours=interval)
            elif unit == "days":
                return IntervalTrigger(days=interval)
            else:
                return IntervalTrigger(seconds=interval)

        elif task.schedule_type == SCHEDULE_TYPE_CRON:
            cron_expr = config.get("cron", "0 0 * * *")
            timezone = config.get("timezone", "Asia/Shanghai")

            # 解析cron表达式
            parts = cron_expr.split()
            if len(parts) >= 5:
                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                    timezone=timezone,
                )

        return None

    async def remove_job(self, task_id: int):
        """从调度器移除任务"""
        job_id = f"task_{task_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info(f"已移除调度任务: {job_id}")

    async def _execute_scheduled_task(self, task_id: int):
        """执行调度任务"""
        async with async_session_local() as db:
            task = await ScheduledTaskService.get_by_id(db, task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            if not task.enabled:
                logger.warning(f"任务已禁用: {task.task_name}")
                return

            # ⚠️ 提前提取属性，避免在异常处理时触发 lazy load
            task_id_val = task.id
            task_name_val = task.task_name
            task_type_val = task.task_type
            task_handler_val = task.handler
            task_params_val = task.handler_params
            task_priority_val = task.priority
            task_max_retries_val = task.max_retries

            # 创建执行记录
            execution_data = TaskExecutionCreate(
                scheduled_task_id=task_id_val,
                task_type=task_type_val,
                task_name=task_name_val,
                handler=task_handler_val,
                handler_params=task_params_val,
                priority=task_priority_val,
                max_retries=task_max_retries_val,
            )

            # 添加关联信息
            if task_type_val == TASK_TYPE_PT_RESOURCE_SYNC and task_params_val:
                site_id = task_params_val.get("site_id")
                if site_id:
                    execution_data.related_type = RELATED_TYPE_PT_SITE
                    execution_data.related_id = site_id
            elif task_type_val == TASK_TYPE_SUBSCRIPTION_CHECK and task_params_val:
                subscription_id = task_params_val.get("subscription_id")
                if subscription_id:
                    execution_data.related_type = RELATED_TYPE_SUBSCRIPTION
                    execution_data.related_id = subscription_id

            execution = await TaskExecutionService.create(db, execution_data)

            # 更新任务状态为运行中
            await ScheduledTaskService.update_run_status(
                db, task_id_val, LAST_RUN_STATUS_RUNNING
            )

            # 执行任务
            start_time = now()
            try:
                await TaskExecutionService.start_execution(db, execution.id)

                # 根据任务类型执行对应的处理器
                result = await self._run_task_handler(db, task, execution)

                # 完成执行
                await TaskExecutionService.complete_execution(db, execution.id, result)

                # 更新任务状态
                duration = int((now() - start_time).total_seconds())
                await ScheduledTaskService.update_run_status(
                    db, task_id_val, LAST_RUN_STATUS_SUCCESS, duration
                )

                logger.info(f"任务执行成功: {task_name_val}")

                # 发布任务完成事件
                try:
                    from app.constants.event import EVENT_TASK_COMPLETED
                    from app.events.bus import event_bus

                    # 格式化时长为人类可读格式
                    if duration < 60:
                        duration_str = f"{duration}秒"
                    elif duration < 3600:
                        minutes = duration // 60
                        seconds = duration % 60
                        duration_str = f"{minutes}分{seconds}秒"
                    else:
                        hours = duration // 3600
                        minutes = (duration % 3600) // 60
                        duration_str = f"{hours}小时{minutes}分"

                    # 格式化结果信息
                    result_str = "成功"
                    if isinstance(result, dict):
                        # 根据不同任务类型提取关键信息
                        if "resources_new" in result:
                            result_str = f"新增{result['resources_new']}个资源，更新{result.get('resources_updated', 0)}个"
                        elif "files_created" in result:
                            result_str = f"创建{result['files_created']}个文件记录"
                        elif "success" in result:
                            result_str = f"成功{result['success']}个，失败{result.get('failed', 0)}个"
                        elif "matched_count" in result:
                            result_str = f"匹配{result['matched_count']}个资源"

                    event_data = {
                        "user_id": 1,  # 固定发送给管理员
                        "task_name": task_name_val,
                        "task_type": task_type_val,
                        "duration": duration_str,  # 使用模板期望的字段名
                        "result": result_str,  # 格式化后的结果
                        "related_type": "task_execution",
                        "related_id": execution.id,
                    }

                    await event_bus.publish(
                        EVENT_TASK_COMPLETED,
                        event_data
                    )

                    logger.debug(f"任务完成事件已发布: {task_name_val}")

                except Exception as e:
                    logger.exception(f"发布任务完成事件失败: {e}")

            except Exception as e:
                error_message = str(e)
                logger.error(f"任务执行失败: {task_name_val}, 错误: {error_message}")

                # 先回滚事务，防止 PendingRollbackError
                try:
                    await db.rollback()
                except Exception:
                    pass

                # 记录失败
                await TaskExecutionService.fail_execution(
                    db, execution.id, error_message, {"exception": type(e).__name__}
                )

                # 更新任务状态
                duration = int((now() - start_time).total_seconds())
                await ScheduledTaskService.update_run_status(
                    db, task_id_val, LAST_RUN_STATUS_FAILED, duration
                )

                # 发布任务失败事件
                try:
                    from app.constants.notification import EVENT_TASK_FAILED
                    from app.events.bus import event_bus

                    event_data = {
                        "broadcast": True,  # 广播消息
                        "task_name": task_name_val,
                        "task_type": task_type_val,
                        "error_message": error_message,
                        "execution_time": duration,
                        "related_type": "task_execution",
                        "related_id": execution.id,
                    }

                    await event_bus.publish(
                        EVENT_TASK_FAILED,
                        event_data
                    )

                    logger.debug(f"任务失败事件已发布: {task_name_val}")

                except Exception as e:
                    logger.exception(f"发布任务失败事件失败: {e}")

    async def _run_task_handler(
        self, db: AsyncSession, task: ScheduledTask, execution
    ) -> Dict[str, Any]:
        """运行任务处理器"""
        from app.tasks.registry import TaskHandlerRegistry

        handler_class = TaskHandlerRegistry.get_handler(task.task_type)
        if not handler_class:
            raise NotImplementedError(f"任务类型 {task.task_type} 暂不支持")

        params = task.handler_params or {}
        return await handler_class.execute(db, params, execution.id)


    async def _execute_task_by_execution(self, execution_id: int):
        """通过执行记录ID执行任务（用于API直接创建的任务）"""
        async with async_session_local() as db:
            execution = await TaskExecutionService.get_by_id(db, execution_id)
            if not execution:
                logger.error(f"执行记录不存在: {execution_id}")
                return

            # 创建临时任务对象
            from app.models.scheduled_task import ScheduledTask
            temp_task = ScheduledTask(
                id=0,  # 临时ID
                task_type=execution.task_type,
                task_name=execution.task_name,
                handler=execution.handler,
                handler_params=execution.handler_params,
                priority=execution.priority,
                max_retries=execution.max_retries or 0,
                schedule_type=SCHEDULE_TYPE_MANUAL,
                enabled=True,
            )

            # 如果关联了调度任务，更新任务状态为运行中
            if execution.scheduled_task_id:
                await ScheduledTaskService.update_run_status(
                    db, execution.scheduled_task_id, LAST_RUN_STATUS_RUNNING
                )

            # 执行任务
            start_time = now()
            try:
                await TaskExecutionService.start_execution(db, execution.id)

                # 根据任务类型执行对应的处理器
                result = await self._run_task_handler(db, temp_task, execution)

                # 完成执行
                await TaskExecutionService.complete_execution(db, execution.id, result)
                
                duration = int((now() - start_time).total_seconds())

                # 如果关联了调度任务，更新任务状态为成功
                if execution.scheduled_task_id:
                    await ScheduledTaskService.update_run_status(
                        db, execution.scheduled_task_id, LAST_RUN_STATUS_SUCCESS, duration
                    )

                logger.info(f"任务执行成功: {temp_task.task_name}")

                # 发布任务完成事件
                try:
                    from app.constants.event import EVENT_TASK_COMPLETED
                    from app.events.bus import event_bus

                    execution_seconds = duration
                    # 格式化时长为人类可读格式
                    if execution_seconds < 60:
                        duration_str = f"{execution_seconds}秒"
                    elif execution_seconds < 3600:
                        minutes = execution_seconds // 60
                        seconds = execution_seconds % 60
                        duration_str = f"{minutes}分{seconds}秒"
                    else:
                        hours = execution_seconds // 3600
                        minutes = (execution_seconds % 3600) // 60
                        duration_str = f"{hours}小时{minutes}分"

                    # 格式化结果信息
                    result_str = "成功"
                    if isinstance(result, dict):
                        # 根据不同任务类型提取关键信息
                        if "resources_new" in result:
                            result_str = f"新增{result['resources_new']}个资源，更新{result.get('resources_updated', 0)}个"
                        elif "files_created" in result:
                            result_str = f"创建{result['files_created']}个文件记录"
                        elif "success" in result:
                            result_str = f"成功{result['success']}个，失败{result.get('failed', 0)}个"
                        elif "matched_count" in result:
                            result_str = f"匹配{result['matched_count']}个资源"

                    event_data = {
                        "user_id": 1,  # 固定发送给管理员
                        "task_name": temp_task.task_name,
                        "task_type": temp_task.task_type,
                        "duration": duration_str,  # 使用模板期望的字段名
                        "result": result_str,  # 格式化后的结果
                        "related_type": "task_execution",
                        "related_id": execution_id,
                    }

                    await event_bus.publish(
                        EVENT_TASK_COMPLETED,
                        event_data
                    )

                    logger.debug(f"任务完成事件已发布: {temp_task.task_name}")

                except Exception as e:
                    logger.exception(f"发布任务完成事件失败: {e}")

            except Exception as e:
                error_message = str(e)
                duration = int((now() - start_time).total_seconds())
                logger.error(f"任务执行失败: {temp_task.task_name}, 错误: {error_message}")

                # 先回滚事务，防止 PendingRollbackError
                try:
                    await db.rollback()
                except Exception:
                    pass

                # 记录失败
                await TaskExecutionService.fail_execution(
                    db, execution_id, error_message, {"exception": type(e).__name__}
                )

                # 如果关联了调度任务，更新任务状态为失败
                if execution.scheduled_task_id:
                    await ScheduledTaskService.update_run_status(
                        db, execution.scheduled_task_id, LAST_RUN_STATUS_FAILED, duration
                    )

                # 发布任务失败事件
                try:
                    from app.constants.notification import EVENT_TASK_FAILED
                    from app.events.bus import event_bus

                    event_data = {
                        "broadcast": True,  # 广播消息
                        "task_name": temp_task.task_name,
                        "task_type": temp_task.task_type,
                        "error_message": error_message,
                        "execution_time": int((now() - start_time).total_seconds()),
                        "related_type": "task_execution",
                        "related_id": execution_id,
                    }

                    await event_bus.publish(
                        EVENT_TASK_FAILED,
                        event_data
                    )

                    logger.debug(f"任务失败事件已发布: {temp_task.task_name}")

                except Exception as event_error:
                    logger.exception(f"发布任务失败事件失败: {event_error}")

    async def run_task_now(self, task_id: int) -> int:
        """立即执行任务（手动触发）"""
        async with async_session_local() as db:
            task = await ScheduledTaskService.get_by_id(db, task_id)
            if not task:
                raise ValueError(f"任务不存在: {task_id}")

            # 创建执行记录
            execution_data = TaskExecutionCreate(
                scheduled_task_id=task.id,
                task_type=task.task_type,
                task_name=f"{task.task_name} (手动触发)",
                handler=task.handler,
                handler_params=task.handler_params,
                priority=task.priority,
                max_retries=task.max_retries,
            )

            if task.task_type == TASK_TYPE_PT_RESOURCE_SYNC and task.handler_params:
                site_id = task.handler_params.get("site_id")
                if site_id:
                    execution_data.related_type = RELATED_TYPE_PT_SITE
                    execution_data.related_id = site_id
            elif task.task_type == TASK_TYPE_SUBSCRIPTION_CHECK and task.handler_params:
                subscription_id = task.handler_params.get("subscription_id")
                if subscription_id:
                    execution_data.related_type = RELATED_TYPE_SUBSCRIPTION
                    execution_data.related_id = subscription_id

            execution = await TaskExecutionService.create(db, execution_data)

        # 在后台执行任务（使用 execution.id 避免重复创建执行记录）
        asyncio.create_task(self._execute_task_by_execution(execution.id))

        return execution.id


# 全局调度器管理器实例
scheduler_manager = SchedulerManager()
