# -*- coding: utf-8 -*-
"""
通知渠道适配器基类
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseNotificationChannel(ABC):
    """
    通知渠道抽象基类

    所有通知渠道适配器都必须继承此类并实现必要的方法
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知渠道

        Args:
            config: 渠道配置（JSON 格式）
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """
        渠道类型标识

        Returns:
            渠道类型字符串 (如 'telegram', 'email', 'webhook')
        """
        pass

    @property
    def supports_markdown(self) -> bool:
        """
        是否支持 Markdown 格式

        Returns:
            True 表示支持 Markdown
        """
        return False

    @property
    def supports_html(self) -> bool:
        """
        是否支持 HTML 格式

        Returns:
            True 表示支持 HTML
        """
        return False

    @property
    def max_message_length(self) -> int:
        """
        最大消息长度限制

        Returns:
            最大字符数（默认 1000）
        """
        return 1000

    @abstractmethod
    async def send(
        self,
        title: str,
        content: str,
        priority: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        发送通知

        Args:
            title: 通知标题
            content: 通知内容
            priority: 优先级 (low/normal/high/urgent)
            **kwargs: 额外参数（不同渠道可能需要不同参数）

        Returns:
            发送结果字典:
            {
                "success": bool,           # 是否成功
                "message": str,            # 结果消息
                "message_id": str,         # 消息ID（如果有）
                "response_data": dict,     # 渠道原始返回数据
                "error": str,              # 错误信息（失败时）
            }

        Raises:
            Exception: 发送失败时抛出异常
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        测试渠道连接

        Returns:
            测试结果字典:
            {
                "success": bool,       # 是否成功
                "message": str,        # 测试结果消息
                "latency_ms": int,     # 延迟（毫秒）
            }

        Raises:
            Exception: 测试失败时抛出异常
        """
        pass

    def truncate_message(self, message: str, max_length: Optional[int] = None) -> str:
        """
        截断过长的消息

        Args:
            message: 原始消息
            max_length: 最大长度（默认使用 self.max_message_length）

        Returns:
            截断后的消息
        """
        max_len = max_length or self.max_message_length
        if len(message) <= max_len:
            return message

        # 保留一些空间用于省略标记
        truncated = message[: max_len - 20]
        return f"{truncated}\n\n... (消息已截断)"

    def validate_config(self, required_fields: list) -> None:
        """
        验证配置是否包含必要字段

        Args:
            required_fields: 必需字段列表

        Raises:
            ValueError: 缺少必需字段时抛出
        """
        missing_fields = [field for field in required_fields if field not in self.config]

        if missing_fields:
            raise ValueError(
                f"{self.channel_type} 渠道配置缺少必需字段: {', '.join(missing_fields)}"
            )

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self.config.get(key, default)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(type={self.channel_type})>"
