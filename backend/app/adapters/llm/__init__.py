# -*- coding: utf-8 -*-
"""
LLM 适配器模块

支持多个 LLM 供应商的统一接口
"""
from typing import Any, Dict, Optional, Type

from app.adapters.llm.base import (
    BaseLLMAdapter,
    ChatCompletionResponse,
    ChatMessage,
    StreamEvent,
    ToolCall,
    ToolDefinition,
)
from app.adapters.llm.zhipu import ZhipuAdapter
from app.constants.ai_agent import (
    LLM_PROVIDER_ZHIPU,
    LLM_PROVIDER_OPENAI,
    LLM_PROVIDER_DEEPSEEK,
    LLM_PROVIDERS,
)


# LLM 适配器注册表
_LLM_ADAPTER_REGISTRY: Dict[str, Type[BaseLLMAdapter]] = {
    LLM_PROVIDER_ZHIPU: ZhipuAdapter,
    # 未来扩展:
    # LLM_PROVIDER_OPENAI: OpenAIAdapter,
    # LLM_PROVIDER_DEEPSEEK: DeepSeekAdapter,
}


def get_llm_adapter(
    provider: str,
    config: Dict[str, Any],
) -> BaseLLMAdapter:
    """
    获取 LLM 适配器实例

    Args:
        provider: 供应商类型
        config: 配置字典

    Returns:
        LLM 适配器实例

    Raises:
        ValueError: 如果供应商不支持
    """
    adapter_class = _LLM_ADAPTER_REGISTRY.get(provider)
    if not adapter_class:
        supported = ", ".join(_LLM_ADAPTER_REGISTRY.keys())
        raise ValueError(f"不支持的 LLM 供应商: {provider}，支持: {supported}")

    return adapter_class(config)


def register_llm_adapter(
    provider: str,
    adapter_class: Type[BaseLLMAdapter],
) -> None:
    """
    注册 LLM 适配器

    Args:
        provider: 供应商类型
        adapter_class: 适配器类
    """
    _LLM_ADAPTER_REGISTRY[provider] = adapter_class


def get_supported_providers() -> list:
    """获取支持的供应商列表"""
    return list(_LLM_ADAPTER_REGISTRY.keys())


__all__ = [
    # 基类
    "BaseLLMAdapter",
    "ChatMessage",
    "ChatCompletionResponse",
    "ToolDefinition",
    "StreamEvent",
    "ToolCall",
    # 适配器
    "ZhipuAdapter",
    # 工厂函数
    "get_llm_adapter",
    "register_llm_adapter",
    "get_supported_providers",
]
