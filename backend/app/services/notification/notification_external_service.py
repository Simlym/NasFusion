# -*- coding: utf-8 -*-
"""
站外通知服务层

负责管理通过外部渠道（Telegram/Email/Webhook）发送的通知日志
包括：日志记录、历史查询、统计分析
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.notification import (
    NOTIFICATION_SEND_STATUS_FAILED,
    NOTIFICATION_SEND_STATUS_SENT,
)
from app.models.notification import NotificationExternal
from app.schemas.notification import NotificationExternalCreate
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class NotificationExternalService:
    """站外通知服务"""

    @staticmethod
    async def create_log(
        db: AsyncSession,
        log_data: NotificationExternalCreate,
    ) -> NotificationExternal:
        """
        创建站外消息发送日志

        Args:
            db: 数据库会话
            log_data: 日志数据

        Returns:
            创建的日志记录
        """
        log = NotificationExternal(**log_data.model_dump())
        db.add(log)
        await db.commit()
        await db.refresh(log)
        logger.info(f"创建站外消息日志: ID={log.id}, 渠道={log.channel_type}, 状态={log.status}")
        return log

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        log_id: int,
    ) -> Optional[NotificationExternal]:
        """
        根据 ID 获取站外消息日志

        Args:
            db: 数据库会话
            log_id: 日志 ID

        Returns:
            日志记录，不存在则返回 None
        """
        stmt = select(NotificationExternal).where(NotificationExternal.id == log_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_logs(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        channel_type: Optional[str] = None,
        notification_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[NotificationExternal], int]:
        """
        获取用户的站外消息历史记录

        Args:
            db: 数据库会话
            user_id: 用户 ID
            skip: 跳过记录数
            limit: 返回记录数
            status: 状态筛选 (pending/sent/failed)
            channel_type: 渠道类型筛选 (telegram/email/webhook)
            notification_type: 通知类型筛选
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            (日志列表, 总数)
        """
        # 构建查询条件
        conditions = [NotificationExternal.user_id == user_id]

        if status:
            conditions.append(NotificationExternal.status == status)
        if channel_type:
            conditions.append(NotificationExternal.channel_type == channel_type)
        if notification_type:
            conditions.append(NotificationExternal.notification_type == notification_type)
        if start_date:
            conditions.append(NotificationExternal.created_at >= start_date)
        if end_date:
            conditions.append(NotificationExternal.created_at <= end_date)

        # 查询总数
        count_stmt = (
            select(func.count())
            .select_from(NotificationExternal)
            .where(and_(*conditions))
        )
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()

        # 查询数据
        stmt = (
            select(NotificationExternal)
            .where(and_(*conditions))
            .order_by(NotificationExternal.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total

    @staticmethod
    async def get_statistics(
        db: AsyncSession,
        user_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取站外消息发送统计

        Args:
            db: 数据库会话
            user_id: 用户 ID
            days: 统计最近多少天的数据

        Returns:
            统计数据字典
        """
        start_date = now() - timedelta(days=days)

        # 基础查询条件
        base_conditions = [
            NotificationExternal.user_id == user_id,
            NotificationExternal.created_at >= start_date,
        ]

        # 1. 总发送数
        total_stmt = (
            select(func.count())
            .select_from(NotificationExternal)
            .where(and_(*base_conditions))
        )
        total_result = await db.execute(total_stmt)
        total_sent = total_result.scalar() or 0

        # 2. 成功数
        success_stmt = (
            select(func.count())
            .select_from(NotificationExternal)
            .where(
                and_(
                    *base_conditions,
                    NotificationExternal.status == NOTIFICATION_SEND_STATUS_SENT,
                )
            )
        )
        success_result = await db.execute(success_stmt)
        success_count = success_result.scalar() or 0

        # 3. 失败数
        failed_stmt = (
            select(func.count())
            .select_from(NotificationExternal)
            .where(
                and_(
                    *base_conditions,
                    NotificationExternal.status == NOTIFICATION_SEND_STATUS_FAILED,
                )
            )
        )
        failed_result = await db.execute(failed_stmt)
        failed_count = failed_result.scalar() or 0

        # 4. 按渠道统计
        channel_stmt = (
            select(
                NotificationExternal.channel_type,
                func.count().label("count"),
            )
            .where(and_(*base_conditions))
            .group_by(NotificationExternal.channel_type)
        )
        channel_result = await db.execute(channel_stmt)
        channel_stats = {row.channel_type: row.count for row in channel_result.all()}

        # 5. 按事件类型统计
        event_stmt = (
            select(
                NotificationExternal.notification_type,
                func.count().label("count"),
            )
            .where(and_(*base_conditions))
            .group_by(NotificationExternal.notification_type)
        )
        event_result = await db.execute(event_stmt)
        event_stats = {row.notification_type: row.count for row in event_result.all()}

        # 6. 按日期统计（最近 N 天）
        daily_stmt = (
            select(
                func.date(NotificationExternal.created_at).label("date"),
                func.count().label("count"),
            )
            .where(and_(*base_conditions))
            .group_by(func.date(NotificationExternal.created_at))
            .order_by(func.date(NotificationExternal.created_at))
        )
        daily_result = await db.execute(daily_stmt)
        daily_stats = {str(row.date): row.count for row in daily_result.all()}

        # 计算成功率
        success_rate = (success_count / total_sent * 100) if total_sent > 0 else 0

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": now().isoformat(),
            "total_sent": total_sent,
            "success_count": success_count,
            "failed_count": failed_count,
            "pending_count": total_sent - success_count - failed_count,
            "success_rate": round(success_rate, 2),
            "channel_distribution": channel_stats,
            "event_distribution": event_stats,
            "daily_distribution": daily_stats,
        }

    @staticmethod
    async def update_status(
        db: AsyncSession,
        log_id: int,
        status: str,
        error_message: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[NotificationExternal]:
        """
        更新站外消息发送状态

        Args:
            db: 数据库会话
            log_id: 日志 ID
            status: 新状态 (pending/sent/failed)
            error_message: 错误信息（失败时）
            response_data: 渠道返回数据

        Returns:
            更新后的日志记录，不存在则返回 None
        """
        log = await NotificationExternalService.get_by_id(db, log_id)
        if not log:
            return None

        log.status = status

        if error_message:
            log.error_message = error_message

        if response_data:
            log.response_data = response_data

        if status == NOTIFICATION_SEND_STATUS_SENT:
            log.sent_at = now()
        elif status == NOTIFICATION_SEND_STATUS_FAILED:
            log.retry_count += 1

        await db.commit()
        await db.refresh(log)

        logger.info(f"更新站外消息状态: ID={log_id}, 状态={status}")
        return log
