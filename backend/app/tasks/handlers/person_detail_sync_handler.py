# -*- coding: utf-8 -*-
"""
人员详情同步处理器
批量从 TMDB 获取人员的 biography/birthday 等详情字段
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.identification.person_service import PersonService
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class PersonDetailSyncHandler(BaseTaskHandler):
    """人员详情同步处理器"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行人员详情批量同步

        Args:
            db: 数据库会话
            params: 处理器参数
                - limit: 每次同步的最大数量 (默认 50)
            execution_id: 任务执行ID

        Returns:
            同步结果
        """
        limit = params.get("limit", 50)

        await TaskExecutionService.append_log(
            db, execution_id, f"开始批量同步人员详情，限制: {limit} 条"
        )

        result = await PersonService.batch_sync_details(db, limit=limit)

        await TaskExecutionService.update_progress(db, execution_id, 100)
        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"人员详情同步完成: 共 {result['total']} 条，"
            f"成功 {result['success']} 条，失败 {result['failed']} 条"
        )

        if result["errors"]:
            for err in result["errors"][:10]:
                await TaskExecutionService.append_log(db, execution_id, f"  错误: {err}")

        return result
