# -*- coding: utf-8 -*-
"""
Telegram Bot 通知渠道适配器
"""
import time
from typing import Any, Dict, Optional

import httpx

from app.adapters.notification_channels.base import BaseNotificationChannel
from app.constants import NOTIFICATION_CHANNEL_TELEGRAM


class TelegramNotificationChannel(BaseNotificationChannel):
    """
    Telegram Bot 通知渠道

    配置示例:
    {
        "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "chat_id": "123456789",
        "parse_mode": "Markdown",  # 可选: Markdown, HTML
        "disable_notification": false,  # 可选: 静音推送
        "disable_web_page_preview": true  # 可选: 禁用链接预览
    }
    """

    TELEGRAM_API_BASE = "https://api.telegram.org"
    MAX_MESSAGE_LENGTH = 4096  # Telegram 消息长度限制

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config(["bot_token", "chat_id"])

        self.bot_token = self.get_config_value("bot_token")
        self.chat_id = self.get_config_value("chat_id")
        self.parse_mode = self.get_config_value("parse_mode", "Markdown")
        self.disable_notification = self.get_config_value("disable_notification", False)
        self.disable_web_page_preview = self.get_config_value(
            "disable_web_page_preview", True
        )

    @property
    def channel_type(self) -> str:
        return NOTIFICATION_CHANNEL_TELEGRAM

    @property
    def supports_markdown(self) -> bool:
        return True

    @property
    def supports_html(self) -> bool:
        return True

    @property
    def max_message_length(self) -> int:
        return self.MAX_MESSAGE_LENGTH

    async def send(
        self,
        title: str,
        content: str,
        priority: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        发送 Telegram 消息

        Args:
            title: 通知标题
            content: 通知内容
            priority: 优先级（Telegram 不支持优先级，仅用于日志）
            **kwargs: 额外参数

        Returns:
            发送结果
        """
        try:
            # 组合标题和内容
            if self.parse_mode == "Markdown":
                full_message = f"**{title}**\n\n{content}"
            elif self.parse_mode == "HTML":
                full_message = f"<b>{title}</b>\n\n{content}"
            else:
                full_message = f"{title}\n\n{content}"

            # 截断过长消息
            full_message = self.truncate_message(full_message, self.MAX_MESSAGE_LENGTH)

            # 构建请求数据
            data = {
                "chat_id": self.chat_id,
                "text": full_message,
                "parse_mode": self.parse_mode,
                "disable_notification": self.disable_notification,
                "disable_web_page_preview": self.disable_web_page_preview,
            }

            # 发送请求
            url = f"{self.TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=data)
                response_data = response.json()

            # 检查响应
            if response.status_code == 200 and response_data.get("ok"):
                message_id = response_data.get("result", {}).get("message_id")
                self.logger.info(
                    f"Telegram 消息发送成功: chat_id={self.chat_id}, message_id={message_id}"
                )

                return {
                    "success": True,
                    "message": "Telegram 消息发送成功",
                    "message_id": str(message_id),
                    "response_data": response_data,
                }
            else:
                error_desc = response_data.get("description", "未知错误")
                self.logger.error(
                    f"Telegram 消息发送失败: {error_desc}, response={response_data}"
                )

                return {
                    "success": False,
                    "message": f"Telegram 发送失败: {error_desc}",
                    "error": error_desc,
                    "response_data": response_data,
                }

        except httpx.TimeoutException:
            error_msg = "Telegram API 请求超时"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error": error_msg,
            }
        except Exception as e:
            error_msg = f"Telegram 发送异常: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试 Telegram Bot 连接

        通过调用 getMe API 验证 bot_token 是否有效
        """
        try:
            start_time = time.time()

            url = f"{self.TELEGRAM_API_BASE}/bot{self.bot_token}/getMe"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response_data = response.json()

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200 and response_data.get("ok"):
                bot_info = response_data.get("result", {})
                bot_name = bot_info.get("username", "Unknown")

                self.logger.info(
                    f"Telegram 连接测试成功: bot={bot_name}, latency={latency_ms}ms"
                )

                return {
                    "success": True,
                    "message": f"连接成功! Bot: @{bot_name}",
                    "latency_ms": latency_ms,
                    "bot_info": bot_info,
                }
            else:
                error_desc = response_data.get("description", "未知错误")
                self.logger.error(f"Telegram 连接测试失败: {error_desc}")

                return {
                    "success": False,
                    "message": f"连接失败: {error_desc}",
                    "latency_ms": latency_ms,
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "连接超时",
                "latency_ms": 10000,
            }
        except Exception as e:
            self.logger.exception(f"Telegram 连接测试异常: {str(e)}")
            return {
                "success": False,
                "message": f"测试异常: {str(e)}",
                "latency_ms": 0,
            }
