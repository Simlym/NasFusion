# -*- coding: utf-8 -*-
"""
通知渠道适配器模块
"""
from typing import Any, Dict

from app.adapters.notification_channels.base import BaseNotificationChannel
from app.adapters.notification_channels.email import EmailNotificationChannel
from app.adapters.notification_channels.telegram import TelegramNotificationChannel
from app.adapters.notification_channels.webhook import WebhookNotificationChannel
from app.constants import (
    NOTIFICATION_CHANNEL_EMAIL,
    NOTIFICATION_CHANNEL_TELEGRAM,
    NOTIFICATION_CHANNEL_WEBHOOK,
)

# 渠道适配器映射
CHANNEL_ADAPTERS = {
    NOTIFICATION_CHANNEL_TELEGRAM: TelegramNotificationChannel,
    NOTIFICATION_CHANNEL_EMAIL: EmailNotificationChannel,
    NOTIFICATION_CHANNEL_WEBHOOK: WebhookNotificationChannel,
}


def get_channel_adapter(
    channel_type: str, config: Dict[str, Any]
) -> BaseNotificationChannel:
    """
    获取通知渠道适配器实例

    Args:
        channel_type: 渠道类型 (telegram/email/webhook 等)
        config: 渠道配置 (JSON 格式)

    Returns:
        渠道适配器实例

    Raises:
        ValueError: 不支持的渠道类型
    """
    adapter_class = CHANNEL_ADAPTERS.get(channel_type)

    if not adapter_class:
        raise ValueError(f"不支持的通知渠道类型: {channel_type}")

    return adapter_class(config)


__all__ = [
    "BaseNotificationChannel",
    "TelegramNotificationChannel",
    "EmailNotificationChannel",
    "WebhookNotificationChannel",
    "get_channel_adapter",
    "CHANNEL_ADAPTERS",
]
