# -*- coding: utf-8 -*-
"""
Webhook 通知渠道适配器
"""
import time
from typing import Any, Dict, Optional

import httpx

from app.adapters.notification_channels.base import BaseNotificationChannel
from app.constants import NOTIFICATION_CHANNEL_WEBHOOK


class WebhookNotificationChannel(BaseNotificationChannel):
    """
    Webhook 通知渠道

    配置示例:
    {
        "url": "https://your-webhook.com/api/notifications",
        "method": "POST",  # 可选: POST, PUT
        "headers": {  # 可选: 自定义请求头
            "Authorization": "Bearer your-token",
            "Content-Type": "application/json"
        },
        "body_template": {  # 可选: 自定义请求体模板
            "title": "{title}",
            "content": "{content}",
            "priority": "{priority}",
            "timestamp": "{timestamp}"
        },
        "timeout": 30  # 可选: 超时时间（秒）
    }
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config(["url"])

        self.url = self.get_config_value("url")
        self.method = self.get_config_value("method", "POST").upper()
        self.headers = self.get_config_value("headers", {})
        self.body_template = self.get_config_value("body_template")
        self.timeout = self.get_config_value("timeout", 30)

        # 验证 HTTP 方法
        if self.method not in ["POST", "PUT"]:
            raise ValueError(f"不支持的 HTTP 方法: {self.method}")

        # 设置默认 Content-Type
        if "Content-Type" not in self.headers:
            self.headers["Content-Type"] = "application/json"

    @property
    def channel_type(self) -> str:
        return NOTIFICATION_CHANNEL_WEBHOOK

    async def send(
        self,
        title: str,
        content: str,
        priority: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        发送 Webhook 通知

        Args:
            title: 通知标题
            content: 通知内容
            priority: 优先级
            **kwargs: 额外参数

        Returns:
            发送结果
        """
        try:
            # 构建请求体
            if self.body_template:
                # 使用自定义模板
                import json
                from datetime import datetime

                # 准备变量替换
                template_vars = {
                    "title": title,
                    "content": content,
                    "priority": priority or "normal",
                    "timestamp": datetime.now().isoformat(),
                    **kwargs,  # 包含额外参数
                }

                # 递归替换模板中的变量
                def replace_vars(obj):
                    if isinstance(obj, str):
                        for key, value in template_vars.items():
                            obj = obj.replace(f"{{{key}}}", str(value))
                        return obj
                    elif isinstance(obj, dict):
                        return {k: replace_vars(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [replace_vars(item) for item in obj]
                    else:
                        return obj

                body = replace_vars(self.body_template)
            else:
                # 使用默认格式
                body = {
                    "title": title,
                    "content": content,
                    "priority": priority or "normal",
                    **kwargs,
                }

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.method == "POST":
                    response = await client.post(
                        self.url, json=body, headers=self.headers
                    )
                else:  # PUT
                    response = await client.put(
                        self.url, json=body, headers=self.headers
                    )

            # 检查响应
            success = response.status_code in [200, 201, 202, 204]

            if success:
                self.logger.info(
                    f"Webhook 发送成功: url={self.url}, status={response.status_code}"
                )

                return {
                    "success": True,
                    "message": f"Webhook 发送成功 (HTTP {response.status_code})",
                    "response_data": {
                        "status_code": response.status_code,
                        "response_body": response.text[:500],  # 限制长度
                    },
                }
            else:
                self.logger.error(
                    f"Webhook 发送失败: url={self.url}, status={response.status_code}, response={response.text[:200]}"
                )

                return {
                    "success": False,
                    "message": f"Webhook 发送失败 (HTTP {response.status_code})",
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "response_data": {
                        "status_code": response.status_code,
                        "response_body": response.text[:500],
                    },
                }

        except httpx.TimeoutException:
            error_msg = f"Webhook 请求超时 (>{self.timeout}s)"
            self.logger.error(f"{error_msg}: url={self.url}")
            return {
                "success": False,
                "message": error_msg,
                "error": error_msg,
            }

        except httpx.ConnectError as e:
            error_msg = f"无法连接到 Webhook: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": "无法连接到 Webhook",
                "error": str(e),
            }

        except Exception as e:
            error_msg = f"Webhook 发送异常: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试 Webhook 连接

        发送一个测试请求到 Webhook URL
        """
        try:
            start_time = time.time()

            # 构建测试消息
            test_body = {
                "title": "NasFusion 通知测试",
                "content": "这是一条测试消息，用于验证 Webhook 配置是否正确。",
                "priority": "normal",
                "test": True,
            }

            # 发送测试请求
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self.method == "POST":
                    response = await client.post(
                        self.url, json=test_body, headers=self.headers
                    )
                else:  # PUT
                    response = await client.put(
                        self.url, json=test_body, headers=self.headers
                    )

            latency_ms = int((time.time() - start_time) * 1000)

            # 检查响应
            success = response.status_code in [200, 201, 202, 204]

            if success:
                self.logger.info(
                    f"Webhook 连接测试成功: url={self.url}, status={response.status_code}, latency={latency_ms}ms"
                )

                return {
                    "success": True,
                    "message": f"连接成功! (HTTP {response.status_code})",
                    "latency_ms": latency_ms,
                }
            else:
                self.logger.error(
                    f"Webhook 连接测试失败: status={response.status_code}"
                )

                return {
                    "success": False,
                    "message": f"连接失败 (HTTP {response.status_code})",
                    "latency_ms": latency_ms,
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "连接超时",
                "latency_ms": 10000,
            }

        except httpx.ConnectError:
            return {
                "success": False,
                "message": "无法连接到 Webhook",
                "latency_ms": 0,
            }

        except Exception as e:
            self.logger.exception(f"Webhook 连接测试异常: {str(e)}")
            return {
                "success": False,
                "message": f"测试异常: {str(e)}",
                "latency_ms": 0,
            }
