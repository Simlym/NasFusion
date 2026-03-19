# -*- coding: utf-8 -*-
"""
通知处理器

监听系统事件并调度通知发送。

工作流程：
    事件总线 → notification_handler → NotificationDispatchService → 发送通知

优势：
    - 业务代码只需发布事件，无需关心通知逻辑
    - 通知系统独立管理，易于测试和维护
"""
import logging
from typing import Any, Dict

from app.core.database import async_session_local
from app.services.notification.notification_dispatch_service import NotificationDispatchService

logger = logging.getLogger(__name__)


async def handle_notification_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    处理通知事件

    接收事件总线发布的事件，调度通知发送。

    Args:
        event_type: 事件类型（如: "download_completed"）
        event_data: 事件数据（需包含 user_id 或 broadcast 标志）

    事件数据格式：
        {
            "user_id": 1,                    # 用户ID（单用户通知时必需）
            "broadcast": False,              # 是否广播消息（默认 False）
            "related_type": "download_task", # 关联资源类型（可选）
            "related_id": 123,               # 关联资源ID（可选）
            ... # 其他业务数据（用于模板渲染）
        }

    示例:
        # 单用户通知
        await event_bus.publish("download_completed", {
            "user_id": 1,
            "media_name": "复仇者联盟",
            "size_gb": 15.5,
            "related_type": "download_task",
            "related_id": 123
        })

        # 广播通知
        await event_bus.publish("system_error", {
            "broadcast": True,
            "title": "系统错误",
            "content": "检测到异常，请尽快处理"
        })
    """
    logger.debug(f"收到通知事件: {event_type}")

    # 创建数据库会话
    async with async_session_local() as db:
        try:
            # 提取通知参数
            user_id = event_data.get("user_id")
            broadcast = event_data.get("broadcast", False)

            # 调度通知
            result = await NotificationDispatchService.dispatch_event(
                db,
                event_type=event_type,
                event_data=event_data,
                user_id=user_id,
                broadcast=broadcast
            )

            logger.info(
                f"通知事件处理完成: {event_type}, "
                f"规则={result.get('total_rules', 0)}, "
                f"站内={result.get('in_app_sent', 0)}, "
                f"渠道={result.get('channel_sent', 0)}, "
                f"失败={result.get('failed', 0)}"
            )

        except Exception as e:
            logger.exception(
                f"通知事件处理失败: {event_type}, 错误: {str(e)}"
            )
