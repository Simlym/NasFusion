# -*- coding: utf-8 -*-
"""
任务处理器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession


class BaseTaskHandler(ABC):
    """任务处理器基类"""

    @staticmethod
    @abstractmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行任务

        Args:
            db: 数据库会话
            params: 处理器参数 (来自 task.handler_params)
            execution_id: 任务执行记录ID (用于进度更新/日志)

        Returns:
            执行结果字典
        """
        pass
