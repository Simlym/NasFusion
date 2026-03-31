# -*- coding: utf-8 -*-
"""
任务执行服务层
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.utils.timezone import now, to_system_tz

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    EXECUTION_STATUS_CANCELLED,
    EXECUTION_STATUS_COMPLETED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_PENDING,
    EXECUTION_STATUS_RUNNING,
    EXECUTION_STATUS_TIMEOUT,
)
from app.models.task_execution import TaskExecution
from app.schemas.task_execution import TaskExecutionCreate, TaskExecutionUpdate

logger = logging.getLogger(__name__)


class TaskExecutionService:
    """任务执行服务"""

    @staticmethod
    async def create(
        db: AsyncSession, execution_data: TaskExecutionCreate
    ) -> TaskExecution:
        """创建任务执行记录"""
        execution = TaskExecution(
            scheduled_task_id=execution_data.scheduled_task_id,
            task_type=execution_data.task_type,
            task_name=execution_data.task_name,
            related_type=execution_data.related_type,
            related_id=execution_data.related_id,
            handler=execution_data.handler,
            handler_params=execution_data.handler_params,
            priority=execution_data.priority,
            scheduled_at=execution_data.scheduled_at or now(),
            max_retries=execution_data.max_retries,
            task_metadata=execution_data.task_metadata,
            status=EXECUTION_STATUS_PENDING,
        )

        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        logger.info(f"创建任务执行记录: {execution.task_name} (ID: {execution.id})")
        return execution

    @staticmethod
    async def get_by_id(db: AsyncSession, execution_id: int) -> Optional[TaskExecution]:
        """根据ID获取执行记录"""
        result = await db.execute(
            select(TaskExecution).where(TaskExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        task_types: Optional[List[str]] = None,
        scheduled_task_id: Optional[int] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[TaskExecution], int]:
        """获取所有执行记录"""
        query = select(TaskExecution)

        # 状态过滤
        if status:
            query = query.where(TaskExecution.status == status)

        # 任务类型过滤（单值或多值）
        if task_types:
            query = query.where(TaskExecution.task_type.in_(task_types))
        elif task_type:
            query = query.where(TaskExecution.task_type == task_type)

        # 定时任务ID过滤
        if scheduled_task_id:
            query = query.where(TaskExecution.scheduled_task_id == scheduled_task_id)

        # 关键字过滤 (任务名称)
        if keyword:
            query = query.where(TaskExecution.task_name.contains(keyword))

        # 日期范围过滤
        if start_date:
            query = query.where(TaskExecution.created_at >= start_date)
        if end_date:
            # 包含结束日期的整天
            end_datetime = end_date.replace(hour=23, minute=59, second=59)
            query = query.where(TaskExecution.created_at <= end_datetime)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar()

        # 排序
        if sort_by == "created_at":
            order_col = TaskExecution.created_at
        elif sort_by == "started_at":
            order_col = TaskExecution.started_at
        elif sort_by == "completed_at":
            order_col = TaskExecution.completed_at
        elif sort_by == "duration":
            order_col = TaskExecution.duration
        else:
            order_col = TaskExecution.created_at

        if sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        # 获取分页数据
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        executions = result.scalars().all()

        return list(executions), total_count

    @staticmethod
    async def get_running_tasks_by_type(
        db: AsyncSession,
        task_type: str
    ) -> List[TaskExecution]:
        """
        获取指定类型的运行中任务（pending 或 running 状态）

        Args:
            db: 数据库会话
            task_type: 任务类型

        Returns:
            运行中的任务列表
        """
        query = select(TaskExecution).where(
            TaskExecution.task_type == task_type,
            or_(
                TaskExecution.status == EXECUTION_STATUS_PENDING,
                TaskExecution.status == EXECUTION_STATUS_RUNNING
            )
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession, execution_id: int, update_data: TaskExecutionUpdate
    ) -> Optional[TaskExecution]:
        """更新执行记录"""
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if not execution:
            return None

        data = update_data.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(execution, field, value)

        await db.commit()
        await db.refresh(execution)

        return execution

    @staticmethod
    async def start_execution(
        db: AsyncSession, execution_id: int, worker_id: str = "main"
    ) -> Optional[TaskExecution]:
        """开始执行任务"""
        from sqlalchemy import update

        # 使用 UPDATE SET 语句直接更新状态，避免 ORM 对象缓存问题
        start_time = now()
        stmt = (
            update(TaskExecution)
            .where(TaskExecution.id == execution_id)
            .values(
                status=EXECUTION_STATUS_RUNNING,
                started_at=start_time,
                worker_id=worker_id,
                progress=0
            )
        )
        await db.execute(stmt)
        await db.commit()

        # 重新加载对象（用于返回和日志）
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if execution:
            logger.info(f"任务开始执行: {execution.task_name} (ID: {execution.id})")

        return execution

    @staticmethod
    async def complete_execution(
        db: AsyncSession,
        execution_id: int,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskExecution]:
        """完成任务执行"""
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if not execution:
            return None

        execution.status = EXECUTION_STATUS_COMPLETED
        execution.completed_at = now()
        execution.progress = 100
        execution.result = result

        if execution.started_at:
            # 确保 started_at 是时区感知的 datetime，避免与 completed_at 相减时报错
            started_at_aware = to_system_tz(execution.started_at)
            execution.duration = int(
                (execution.completed_at - started_at_aware).total_seconds()
            )

        await db.commit()
        await db.refresh(execution)

        logger.info(f"任务执行完成: {execution.task_name} (ID: {execution.id})")
        return execution

    @staticmethod
    async def fail_execution(
        db: AsyncSession,
        execution_id: int,
        error_message: str,
        error_detail: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskExecution]:
        """任务执行失败"""
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if not execution:
            return None

        execution.completed_at = now()
        execution.error_message = error_message
        execution.error_detail = error_detail

        if execution.started_at:
            # 确保 started_at 是时区感知的 datetime，避免与 completed_at 相减时报错
            started_at_aware = to_system_tz(execution.started_at)
            execution.duration = int(
                (execution.completed_at - started_at_aware).total_seconds()
            )

        # 检查是否可以重试
        if execution.retry_count < execution.max_retries:
            execution.status = EXECUTION_STATUS_PENDING
            execution.retry_count += 1
            # 使用指数退避计算下次重试时间
            retry_delay = 60 * (2 ** (execution.retry_count - 1))  # 60s, 120s, 240s...
            execution.next_retry_at = now() + timedelta(seconds=retry_delay)
            logger.warning(
                f"任务执行失败，将在 {retry_delay}秒后重试: {execution.task_name} "
                f"(重试 {execution.retry_count}/{execution.max_retries})"
            )
        else:
            execution.status = EXECUTION_STATUS_FAILED
            logger.error(f"任务执行失败，已达最大重试次数: {execution.task_name}")

        await db.commit()
        await db.refresh(execution)

        return execution

    @staticmethod
    async def cancel_execution(
        db: AsyncSession, execution_id: int
    ) -> Optional[TaskExecution]:
        """取消任务执行"""
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if not execution:
            return None

        if execution.status not in [EXECUTION_STATUS_PENDING, EXECUTION_STATUS_RUNNING]:
            raise ValueError(f"无法取消状态为 {execution.status} 的任务")

        execution.status = EXECUTION_STATUS_CANCELLED
        execution.completed_at = now()

        if execution.started_at:
            # 确保 started_at 是时区感知的 datetime，避免与 completed_at 相减时报错
            started_at_aware = to_system_tz(execution.started_at)
            execution.duration = int(
                (execution.completed_at - started_at_aware).total_seconds()
            )

        await db.commit()
        await db.refresh(execution)

        logger.info(f"任务已取消: {execution.task_name} (ID: {execution.id})")
        return execution

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        execution_id: int,
        progress: int,
        progress_detail: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskExecution]:
        """更新任务进度"""
        from sqlalchemy import update

        # 使用 UPDATE SET 语句，只更新 progress 和 progress_detail 字段
        # 避免覆盖其他字段（如 status, started_at 等）
        update_values = {"progress": min(100, max(0, progress))}
        if progress_detail is not None:
            update_values["progress_detail"] = progress_detail

        stmt = (
            update(TaskExecution)
            .where(TaskExecution.id == execution_id)
            .values(**update_values)
        )
        await db.execute(stmt)
        await db.commit()

        # 重新加载对象
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        return execution

    @staticmethod
    async def append_log(
        db: AsyncSession, execution_id: int, log_message: str
    ) -> Optional[TaskExecution]:
        """追加任务日志"""
        from sqlalchemy import update, select

        # 先获取当前的 logs 值
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if not execution:
            return None

        timestamp = now().strftime("%Y-%m-%d %H:%M:%S")
        new_log = f"[{timestamp}] {log_message}\n"

        if execution.logs:
            updated_logs = execution.logs + new_log
        else:
            updated_logs = new_log

        # 使用 UPDATE SET 语句，只更新 logs 字段
        stmt = (
            update(TaskExecution)
            .where(TaskExecution.id == execution_id)
            .values(logs=updated_logs)
        )
        await db.execute(stmt)
        await db.commit()

        # 重新加载对象
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        return execution

    @staticmethod
    async def get_queue_status(db: AsyncSession) -> Dict[str, Any]:
        """获取任务队列状态"""
        # 运行中的任务
        running_query = select(TaskExecution).where(
            TaskExecution.status == EXECUTION_STATUS_RUNNING
        ).order_by(TaskExecution.started_at.desc())
        running_result = await db.execute(running_query)
        running = list(running_result.scalars().all())

        # 等待中的任务
        pending_query = select(TaskExecution).where(
            TaskExecution.status == EXECUTION_STATUS_PENDING
        ).order_by(TaskExecution.priority.desc(), TaskExecution.scheduled_at)
        pending_result = await db.execute(pending_query)
        pending = list(pending_result.scalars().all())

        # 最近完成的任务（最近24小时内）
        recent_time = now() - timedelta(hours=24)
        recent_query = (
            select(TaskExecution)
            .where(
                TaskExecution.status.in_(
                    [
                        EXECUTION_STATUS_COMPLETED,
                        EXECUTION_STATUS_FAILED,
                        EXECUTION_STATUS_CANCELLED,
                    ]
                ),
                TaskExecution.completed_at >= recent_time,
            )
            .order_by(TaskExecution.completed_at.desc())
            .limit(20)
        )
        recent_result = await db.execute(recent_query)
        recent_completed = list(recent_result.scalars().all())

        return {
            "running": running,
            "pending": pending,
            "recent_completed": recent_completed,
        }

    @staticmethod
    async def cleanup_old_executions(
        db: AsyncSession, days: int = 30
    ) -> int:
        """清理旧的执行记录"""
        cutoff_time = now() - timedelta(days=days)

        # 只删除已完成、失败或取消的任务
        query = select(TaskExecution).where(
            TaskExecution.status.in_(
                [
                    EXECUTION_STATUS_COMPLETED,
                    EXECUTION_STATUS_FAILED,
                    EXECUTION_STATUS_CANCELLED,
                    EXECUTION_STATUS_TIMEOUT,
                ]
            ),
            TaskExecution.created_at < cutoff_time,
        )
        result = await db.execute(query)
        old_executions = result.scalars().all()

        count = 0
        for execution in old_executions:
            await db.delete(execution)
            count += 1

        await db.commit()
        logger.info(f"清理了 {count} 条旧的任务执行记录")
        return count
