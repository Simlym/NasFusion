# -*- coding: utf-8 -*-
"""
站内通知服务层

负责管理用户在系统内收到的通知（站内信）
包括：通知创建、查询、标记已读、删除等
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    DEFAULT_NOTIFICATION_EXPIRE_DAYS,
    EVENT_PRIORITY_MAPPING,
    NOTIFICATION_PRIORITY_NORMAL,
    NOTIFICATION_STATUS_ARCHIVED,
    NOTIFICATION_STATUS_READ,
    NOTIFICATION_STATUS_UNREAD,
)
from app.models.notification import NotificationInternal
from app.schemas.notification import NotificationInternalCreate, NotificationInternalUpdate
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class NotificationInternalService:
    """站内通知服务"""

    @staticmethod
    async def create_notification(
        db: AsyncSession, notification_data: NotificationInternalCreate
    ) -> NotificationInternal:
        """
        创建系统内通知

        Args:
            db: 数据库会话
            notification_data: 通知数据

        Returns:
            创建的通知记录
        """
        # 自动设置优先级（如果未提供）
        priority = notification_data.priority
        if priority == "normal" and notification_data.notification_type in EVENT_PRIORITY_MAPPING:
            priority = EVENT_PRIORITY_MAPPING[notification_data.notification_type]

        # 自动设置过期时间（如果未提供）
        expires_at = notification_data.expires_at
        if expires_at is None:
            expires_at = now() + timedelta(days=DEFAULT_NOTIFICATION_EXPIRE_DAYS)

        notification = NotificationInternal(
            user_id=notification_data.user_id,
            notification_type=notification_data.notification_type,
            title=notification_data.title,
            content=notification_data.content,
            priority=priority,
            status=NOTIFICATION_STATUS_UNREAD,
            related_type=notification_data.related_type,
            related_id=notification_data.related_id,
            extra_data=notification_data.extra_data,
            expires_at=expires_at,
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        logger.info(
            f"创建通知: {notification.title} (用户ID: {notification.user_id}, "
            f"类型: {notification.notification_type}, 优先级: {notification.priority})"
        )
        return notification

    @staticmethod
    async def send_in_app_notification(
        db: AsyncSession,
        event_type: str,
        title: str,
        content: str,
        user_id: Optional[int] = None,
        related_type: Optional[str] = None,
        related_id: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        priority: Optional[str] = None,
    ) -> NotificationInternal:
        """
        发送系统内通知（快捷方法）

        Args:
            db: 数据库会话
            event_type: 事件类型
            title: 通知标题
            content: 通知内容
            user_id: 用户ID (None表示系统广播)
            related_type: 关联资源类型
            related_id: 关联资源ID
            extra_data: 扩展数据
            priority: 优先级 (如果不提供，自动根据event_type映射)

        Returns:
            创建的通知记录
        """
        notification_data = NotificationInternalCreate(
            user_id=user_id,
            notification_type=event_type,
            title=title,
            content=content,
            priority=priority or NOTIFICATION_PRIORITY_NORMAL,
            related_type=related_type,
            related_id=related_id,
            extra_data=extra_data,
        )

        return await NotificationInternalService.create_notification(db, notification_data)

    @staticmethod
    async def get_by_id(
        db: AsyncSession, notification_id: int
    ) -> Optional[NotificationInternal]:
        """根据ID获取通知"""
        result = await db.execute(
            select(NotificationInternal).where(NotificationInternal.id == notification_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
        priority: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_broadcast: bool = True,
    ) -> tuple[List[NotificationInternal], int]:
        """
        获取用户通知列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            skip: 跳过数量
            limit: 返回数量
            status: 状态筛选
            notification_type: 通知类型筛选
            priority: 优先级筛选
            start_date: 开始日期
            end_date: 结束日期
            include_broadcast: 是否包含系统广播 (user_id=NULL)

        Returns:
            (通知列表, 总数)
        """
        # 构建基础查询
        query = select(NotificationInternal)

        # 用户ID过滤（包含用户专属 + 系统广播）
        if include_broadcast:
            query = query.where(
                or_(
                    NotificationInternal.user_id == user_id,
                    NotificationInternal.user_id.is_(None),  # 系统广播
                )
            )
        else:
            query = query.where(NotificationInternal.user_id == user_id)

        # 状态过滤
        if status:
            query = query.where(NotificationInternal.status == status)

        # 通知类型过滤
        if notification_type:
            query = query.where(NotificationInternal.notification_type == notification_type)

        # 优先级过滤
        if priority:
            query = query.where(NotificationInternal.priority == priority)

        # 日期范围过滤
        if start_date:
            query = query.where(NotificationInternal.created_at >= start_date)
        if end_date:
            end_datetime = end_date.replace(hour=23, minute=59, second=59)
            query = query.where(NotificationInternal.created_at <= end_datetime)

        # 过滤已过期的通知
        query = query.where(
            or_(
                NotificationInternal.expires_at.is_(None),
                NotificationInternal.expires_at > now(),
            )
        )

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 按创建时间倒序排序
        query = query.order_by(NotificationInternal.created_at.desc())

        # 分页
        query = query.offset(skip).limit(limit)

        # 执行查询
        result = await db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: int) -> int:
        """
        获取用户未读消息数量

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            未读消息数量
        """
        query = select(func.count()).where(
            and_(
                or_(
                    NotificationInternal.user_id == user_id,
                    NotificationInternal.user_id.is_(None),  # 系统广播
                ),
                NotificationInternal.status == NOTIFICATION_STATUS_UNREAD,
                or_(
                    NotificationInternal.expires_at.is_(None),
                    NotificationInternal.expires_at > now(),
                ),
            )
        )

        result = await db.execute(query)
        return result.scalar()

    @staticmethod
    async def mark_as_read(
        db: AsyncSession, notification_id: int, user_id: Optional[int] = None
    ) -> Optional[NotificationInternal]:
        """
        标记通知为已读

        Args:
            db: 数据库会话
            notification_id: 通知ID
            user_id: 用户ID (用于权限检查)

        Returns:
            更新后的通知记录，如果无权限返回None
        """
        # 查询通知
        query = select(NotificationInternal).where(NotificationInternal.id == notification_id)

        # 权限检查：只能标记自己的通知或系统广播
        if user_id is not None:
            query = query.where(
                or_(
                    NotificationInternal.user_id == user_id,
                    NotificationInternal.user_id.is_(None),
                )
            )

        result = await db.execute(query)
        notification = result.scalar_one_or_none()

        if not notification:
            logger.warning(f"通知不存在或无权限: notification_id={notification_id}, user_id={user_id}")
            return None

        # 更新状态
        notification.status = NOTIFICATION_STATUS_READ
        notification.read_at = now()

        await db.commit()
        await db.refresh(notification)

        logger.info(f"标记通知已读: {notification.title} (ID: {notification.id})")
        return notification

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
        """
        标记用户所有未读通知为已读

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            更新的通知数量
        """
        # 查询所有未读通知
        query = select(NotificationInternal).where(
            and_(
                or_(
                    NotificationInternal.user_id == user_id,
                    NotificationInternal.user_id.is_(None),
                ),
                NotificationInternal.status == NOTIFICATION_STATUS_UNREAD,
            )
        )

        result = await db.execute(query)
        notifications = result.scalars().all()

        # 批量更新
        count = 0
        for notification in notifications:
            notification.status = NOTIFICATION_STATUS_READ
            notification.read_at = now()
            count += 1

        await db.commit()

        logger.info(f"批量标记已读: 用户ID={user_id}, 更新数量={count}")
        return count

    @staticmethod
    async def update_notification(
        db: AsyncSession,
        notification_id: int,
        update_data: NotificationInternalUpdate,
        user_id: Optional[int] = None,
    ) -> Optional[NotificationInternal]:
        """
        更新通知

        Args:
            db: 数据库会话
            notification_id: 通知ID
            update_data: 更新数据
            user_id: 用户ID (用于权限检查)

        Returns:
            更新后的通知记录
        """
        # 查询通知
        query = select(NotificationInternal).where(NotificationInternal.id == notification_id)

        if user_id is not None:
            query = query.where(
                or_(
                    NotificationInternal.user_id == user_id,
                    NotificationInternal.user_id.is_(None),
                )
            )

        result = await db.execute(query)
        notification = result.scalar_one_or_none()

        if not notification:
            return None

        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(notification, key, value)

        await db.commit()
        await db.refresh(notification)

        logger.info(f"更新通知: {notification.title} (ID: {notification.id})")
        return notification

    @staticmethod
    async def delete_notification(
        db: AsyncSession, notification_id: int, user_id: Optional[int] = None
    ) -> bool:
        """
        删除通知

        Args:
            db: 数据库会话
            notification_id: 通知ID
            user_id: 用户ID (用于权限检查)

        Returns:
            是否删除成功
        """
        # 查询通知
        query = select(NotificationInternal).where(NotificationInternal.id == notification_id)

        if user_id is not None:
            query = query.where(NotificationInternal.user_id == user_id)

        result = await db.execute(query)
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        await db.delete(notification)
        await db.commit()

        logger.info(f"删除通知: {notification.title} (ID: {notification.id})")
        return True

    @staticmethod
    async def cleanup_expired(db: AsyncSession) -> int:
        """
        清理已过期的通知

        Args:
            db: 数据库会话

        Returns:
            清理的通知数量
        """
        # 查询过期通知
        query = select(NotificationInternal).where(
            and_(
                NotificationInternal.expires_at.is_not(None),
                NotificationInternal.expires_at <= now(),
            )
        )

        result = await db.execute(query)
        expired_notifications = result.scalars().all()

        # 批量删除
        count = 0
        for notification in expired_notifications:
            await db.delete(notification)
            count += 1

        await db.commit()

        if count > 0:
            logger.info(f"清理过期通知: 删除数量={count}")

        return count

    @staticmethod
    async def archive_read_notifications(
        db: AsyncSession, user_id: int, days_old: int = 30
    ) -> int:
        """
        归档旧的已读通知

        Args:
            db: 数据库会话
            user_id: 用户ID
            days_old: 多少天前的已读通知

        Returns:
            归档的通知数量
        """
        cutoff_date = now() - timedelta(days=days_old)

        # 查询旧的已读通知
        query = select(NotificationInternal).where(
            and_(
                NotificationInternal.user_id == user_id,
                NotificationInternal.status == NOTIFICATION_STATUS_READ,
                NotificationInternal.read_at <= cutoff_date,
            )
        )

        result = await db.execute(query)
        notifications = result.scalars().all()

        # 批量归档
        count = 0
        for notification in notifications:
            notification.status = NOTIFICATION_STATUS_ARCHIVED
            count += 1

        await db.commit()

        if count > 0:
            logger.info(f"归档旧通知: 用户ID={user_id}, 归档数量={count}")

        return count
