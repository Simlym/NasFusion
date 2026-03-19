# -*- coding: utf-8 -*-
"""
任务执行记录清理处理器
"""
import logging
from typing import Dict, Any
from datetime import timedelta

from sqlalchemy import delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.models.task_execution import TaskExecution
from app.services.task.task_execution_service import TaskExecutionService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class TaskExecutionCleanupHandler(BaseTaskHandler):
    """清理任务执行历史"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行清理任务

        Args:
            db: 数据库会话
            params: 处理器参数
                - days: 清理多少天前的记录 (默认 7)
                - keep_failed: 是否保留失败记录 (默认 True)
            execution_id: 任务执行ID

        Returns:
            清理结果
        """
        days = params.get("days", 7)
        keep_failed = params.get("keep_failed", True)

        await TaskExecutionService.append_log(
            db, execution_id, f"开始清理 {days} 天前的执行记录"
        )

        cutoff_date = now() - timedelta(days=days)

        # 构建删除条件
        conditions = [
            TaskExecution.completed_at < cutoff_date,
            TaskExecution.status == 'completed'
        ]

        if not keep_failed:
            conditions = [TaskExecution.completed_at < cutoff_date]

        # 执行删除
        result = await db.execute(
            delete(TaskExecution).where(and_(*conditions))
        )
        await db.commit()

        deleted_count = result.rowcount

        await TaskExecutionService.update_progress(db, execution_id, 100)
        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"清理完成: 删除 {deleted_count} 条记录"
        )

        return {
            "deleted_count": deleted_count,
            "cutoff_date": str(cutoff_date),
            "keep_failed": keep_failed
        }
