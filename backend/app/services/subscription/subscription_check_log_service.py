# -*- coding: utf-8 -*-
"""
订阅检查日志服务层
"""
import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SubscriptionCheckLog
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class SubscriptionCheckLogService:
    """订阅检查日志服务"""

    @staticmethod
    async def create_log(
        db: AsyncSession,
        subscription_id: int,
        **kwargs
    ) -> SubscriptionCheckLog:
        """
        创建订阅检查日志

        Args:
            db: 数据库会话
            subscription_id: 订阅ID
            **kwargs: 其他日志字段

        Returns:
            SubscriptionCheckLog: 创建的日志
        """
        log = SubscriptionCheckLog(
            subscription_id=subscription_id,
            check_at=now(),
            **kwargs
        )

        db.add(log)
        await db.commit()
        await db.refresh(log)

        logger.debug(f"创建订阅检查日志: 订阅{subscription_id}")
        return log

    @staticmethod
    async def get_by_id(db: AsyncSession, log_id: int) -> Optional[SubscriptionCheckLog]:
        """通过ID获取日志"""
        result = await db.execute(select(SubscriptionCheckLog).where(SubscriptionCheckLog.id == log_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        subscription_id: Optional[int] = None,
        success: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SubscriptionCheckLog], int]:
        """
        获取检查日志列表

        Args:
            db: 数据库会话
            subscription_id: 订阅ID过滤
            success: 成功状态过滤
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[SubscriptionCheckLog], int]: 日志列表和总数
        """
        # 构建查询
        query = select(SubscriptionCheckLog)

        # 添加过滤条件
        if subscription_id is not None:
            query = query.where(SubscriptionCheckLog.subscription_id == subscription_id)
        if success is not None:
            query = query.where(SubscriptionCheckLog.success == success)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(SubscriptionCheckLog.check_at.desc())

        # 执行查询
        result = await db.execute(query)
        logs = result.scalars().all()

        return list(logs), total

    @staticmethod
    async def get_latest_log(
        db: AsyncSession, subscription_id: int
    ) -> Optional[SubscriptionCheckLog]:
        """获取订阅的最新检查日志"""
        query = (
            select(SubscriptionCheckLog)
            .where(SubscriptionCheckLog.subscription_id == subscription_id)
            .order_by(SubscriptionCheckLog.check_at.desc())
            .limit(1)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_old_logs(db: AsyncSession, days: int = 30) -> int:
        """
        删除旧的检查日志

        Args:
            db: 数据库会话
            days: 保留天数

        Returns:
            int: 删除的日志数量
        """
        from datetime import timedelta

        cutoff_time = now() - timedelta(days=days)

        # 查询要删除的日志
        query = select(SubscriptionCheckLog).where(SubscriptionCheckLog.check_at < cutoff_time)
        result = await db.execute(query)
        logs_to_delete = result.scalars().all()

        count = len(logs_to_delete)
        if count > 0:
            for log in logs_to_delete:
                await db.delete(log)

            await db.commit()
            logger.info(f"删除了{count}条旧的订阅检查日志（{days}天前）")

        return count
