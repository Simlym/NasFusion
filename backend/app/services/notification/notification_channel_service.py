# -*- coding: utf-8 -*-
"""
通知渠道服务层
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notification_channels import get_channel_adapter
from app.constants import (
    NOTIFICATION_CHANNEL_STATUS_ERROR,
    NOTIFICATION_CHANNEL_STATUS_HEALTHY,
    NOTIFICATION_CHANNEL_STATUS_TESTING,
)
from app.models.notification import NotificationChannel
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class NotificationChannelService:
    """通知渠道服务"""

    @staticmethod
    async def get_by_id(
        db: AsyncSession, channel_id: int
    ) -> Optional[NotificationChannel]:
        """根据ID获取渠道"""
        result = await db.execute(
            select(NotificationChannel).where(NotificationChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_channels(
        db: AsyncSession,
        user_id: int,
        enabled_only: bool = False,
        channel_type: Optional[str] = None,
    ) -> List[NotificationChannel]:
        """
        获取用户的通知渠道列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            enabled_only: 仅返回启用的渠道
            channel_type: 渠道类型筛选

        Returns:
            渠道列表
        """
        query = select(NotificationChannel).where(
            NotificationChannel.user_id == user_id
        )

        if enabled_only:
            query = query.where(NotificationChannel.enabled == True)

        if channel_type:
            query = query.where(NotificationChannel.channel_type == channel_type)

        # 按优先级倒序排序
        query = query.order_by(NotificationChannel.priority.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_enabled_channels(
        db: AsyncSession, user_id: int, channel_type: Optional[str] = None
    ) -> List[NotificationChannel]:
        """
        获取用户启用的通知渠道

        Args:
            db: 数据库会话
            user_id: 用户ID
            channel_type: 渠道类型（可选）

        Returns:
            启用的渠道列表
        """
        return await NotificationChannelService.get_user_channels(
            db, user_id, enabled_only=True, channel_type=channel_type
        )

    @staticmethod
    async def test_channel(
        db: AsyncSession, channel_id: int
    ) -> Dict[str, Any]:
        """
        测试通知渠道连接

        Args:
            db: 数据库会话
            channel_id: 渠道ID

        Returns:
            测试结果
        """
        # 查询渠道
        channel = await NotificationChannelService.get_by_id(db, channel_id)

        if not channel:
            return {
                "success": False,
                "message": "渠道不存在",
            }

        try:
            # 更新状态为测试中
            channel.status = NOTIFICATION_CHANNEL_STATUS_TESTING
            await db.commit()

            # 获取适配器
            adapter = get_channel_adapter(channel.channel_type, channel.config)

            # 测试连接
            test_result = await adapter.test_connection()

            # 更新渠道状态
            channel.status = (
                NOTIFICATION_CHANNEL_STATUS_HEALTHY
                if test_result["success"]
                else NOTIFICATION_CHANNEL_STATUS_ERROR
            )
            channel.last_test_at = now()
            channel.last_test_result = test_result.get("message", "")

            if test_result["success"]:
                channel.last_success_at = now()
                channel.consecutive_failures = 0
            else:
                channel.consecutive_failures += 1

            await db.commit()
            await db.refresh(channel)

            logger.info(
                f"渠道测试完成: channel_id={channel_id}, success={test_result['success']}"
            )

            return test_result

        except ValueError as e:
            # 不支持的渠道类型或配置错误
            error_msg = str(e)
            logger.error(f"渠道测试失败: {error_msg}")

            channel.status = NOTIFICATION_CHANNEL_STATUS_ERROR
            channel.last_test_at = now()
            channel.last_test_result = error_msg
            channel.consecutive_failures += 1

            await db.commit()

            return {
                "success": False,
                "message": error_msg,
            }

        except Exception as e:
            # 未知错误
            error_msg = f"测试异常: {str(e)}"
            logger.exception(f"渠道测试异常: channel_id={channel_id}")

            channel.status = NOTIFICATION_CHANNEL_STATUS_ERROR
            channel.last_test_at = now()
            channel.last_test_result = error_msg
            channel.consecutive_failures += 1

            await db.commit()

            return {
                "success": False,
                "message": error_msg,
            }

    @staticmethod
    async def send_via_channel(
        db: AsyncSession,
        channel_id: int,
        title: str,
        content: str,
        priority: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        通过指定渠道发送通知

        Args:
            db: 数据库会话
            channel_id: 渠道ID
            title: 通知标题
            content: 通知内容
            priority: 优先级
            **kwargs: 额外参数

        Returns:
            发送结果
        """
        # 查询渠道
        channel = await NotificationChannelService.get_by_id(db, channel_id)

        if not channel:
            return {
                "success": False,
                "message": "渠道不存在",
            }

        if not channel.enabled:
            return {
                "success": False,
                "message": "渠道未启用",
            }

        try:
            # 获取适配器
            adapter = get_channel_adapter(channel.channel_type, channel.config)

            # 发送通知
            send_result = await adapter.send(
                title=title, content=content, priority=priority, **kwargs
            )

            # 更新渠道统计
            if send_result["success"]:
                channel.status = NOTIFICATION_CHANNEL_STATUS_HEALTHY
                channel.last_success_at = now()
                channel.consecutive_failures = 0
            else:
                channel.status = NOTIFICATION_CHANNEL_STATUS_ERROR
                channel.consecutive_failures += 1

                # 连续失败超过阈值时自动禁用
                if channel.consecutive_failures >= 5:
                    channel.enabled = False
                    logger.warning(
                        f"渠道连续失败 {channel.consecutive_failures} 次，已自动禁用: "
                        f"channel_id={channel_id}, type={channel.channel_type}"
                    )

            await db.commit()

            logger.info(
                f"渠道发送完成: channel_id={channel_id}, success={send_result['success']}"
            )

            return send_result

        except ValueError as e:
            error_msg = str(e)
            logger.error(f"渠道发送失败: {error_msg}")

            channel.status = NOTIFICATION_CHANNEL_STATUS_ERROR
            channel.consecutive_failures += 1

            await db.commit()

            return {
                "success": False,
                "message": error_msg,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            logger.exception(f"渠道发送异常: channel_id={channel_id}")

            channel.status = NOTIFICATION_CHANNEL_STATUS_ERROR
            channel.consecutive_failures += 1

            await db.commit()

            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

    @staticmethod
    async def update_channel_health(
        db: AsyncSession, channel_id: int, success: bool
    ) -> None:
        """
        更新渠道健康状态

        Args:
            db: 数据库会话
            channel_id: 渠道ID
            success: 是否成功
        """
        channel = await NotificationChannelService.get_by_id(db, channel_id)

        if not channel:
            return

        if success:
            channel.status = NOTIFICATION_CHANNEL_STATUS_HEALTHY
            channel.last_success_at = now()
            channel.consecutive_failures = 0
        else:
            channel.status = NOTIFICATION_CHANNEL_STATUS_ERROR
            channel.consecutive_failures += 1

            # 连续失败超过阈值时自动禁用
            if channel.consecutive_failures >= 5:
                channel.enabled = False
                logger.warning(
                    f"渠道连续失败 {channel.consecutive_failures} 次，已自动禁用: "
                    f"channel_id={channel_id}"
                )

        await db.commit()
