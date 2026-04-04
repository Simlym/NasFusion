# -*- coding: utf-8 -*-
"""
LLM 适配器基类
定义大语言模型集成的统一接口
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # system, user, assistant, tool
    content: str  # 文本内容，或 JSON 字符串（多模态时）
    name: Optional[str] = None  # 工具名称（当 role=tool 时）
    tool_call_id: Optional[str] = None  # 工具调用ID
    images: Optional[List[str]] = None  # Base64 编码的图片列表（多模态）
    
    class Config:
        extra = "allow"  # 允许额外字段用于多模态


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema 格式


class ToolCall(BaseModel):
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


class StreamEvent(BaseModel):
    """流式事件"""
    type: str  # "content", "tool_calls", "done", "error"
    content: Optional[str] = None  # type=content 时的文本片段
    tool_calls: Optional[List[ToolCall]] = None  # type=tool_calls 时的完整工具调用列表
    finish_reason: Optional[str] = None  # type=done 时的结束原因


class ChatCompletionResponse(BaseModel):
    """聊天完成响应"""
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: str = "stop"  # stop, tool_calls, length
    usage: Optional[Dict[str, int]] = None  # prompt_tokens, completion_tokens, total_tokens


class BaseLLMAdapter(ABC):
    """
    LLM 适配器基类

    所有 LLM 供应商适配器都应继承此类并实现抽象方法
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化适配器

        Args:
            config: 配置字典，包含 api_key, model, temperature 等
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # 通用配置
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)
        self.top_p = config.get("top_p", 0.9)
        self.timeout = config.get("timeout", 60)
        self.proxy = config.get("proxy")

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """供应商名称"""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass

    @property
    def supports_tools(self) -> bool:
        """是否支持工具调用"""
        return True

    @property
    def supports_streaming(self) -> bool:
        """是否支持流式输出"""
        return True

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,  # auto, none, required
        **kwargs
    ) -> ChatCompletionResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具列表
            tool_choice: 工具选择策略
            **kwargs: 其他参数

        Returns:
            ChatCompletionResponse
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        发送流式聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具列表
            tool_choice: 工具选择策略
            **kwargs: 其他参数

        Yields:
            StreamEvent 事件（content/tool_calls/done）
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        Returns:
            包含 success, message, latency_ms 等字段的字典
        """
        pass

    def validate_config(self, required_fields: List[str]) -> None:
        """
        验证配置

        Args:
            required_fields: 必需的配置字段

        Raises:
            ValueError: 如果缺少必需字段
        """
        missing = [f for f in required_fields if not self.config.get(f)]
        if missing:
            raise ValueError(f"缺少必需配置: {', '.join(missing)}")

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
