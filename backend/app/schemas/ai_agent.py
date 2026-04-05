# -*- coding: utf-8 -*-
"""
AI Agent Pydantic 模型
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema


# ===== AI Agent 配置 =====

class AIAgentConfigBase(BaseModel):
    """AI Agent 配置基础"""
    llm_config_id: Optional[int] = Field(default=None, description="关联的全局LLM配置ID")
    model: str = Field(default="glm-4-flash", description="模型")
    temperature: str = Field(default="0.7", description="温度参数")
    max_tokens: int = Field(default=2048, description="最大Token数")
    top_p: str = Field(default="0.9", description="Top-P参数")
    is_enabled: bool = Field(default=False, description="是否启用")
    enable_tools: bool = Field(default=True, description="是否启用工具")
    enable_streaming: bool = Field(default=True, description="是否启用流式输出")
    system_prompt: Optional[str] = Field(default=None, description="自定义系统提示词")


class AIAgentConfigCreate(AIAgentConfigBase):
    """创建 AI Agent 配置"""
    # 向后兼容：仍然支持直接传入供应商信息
    provider: Optional[str] = Field(default=None, description="LLM供应商（兼容旧模式）")
    api_key: Optional[str] = Field(default=None, description="API密钥（兼容旧模式）")
    api_base: Optional[str] = Field(default=None, description="API基础URL（兼容旧模式）")
    proxy: Optional[str] = Field(default=None, description="代理服务器（兼容旧模式）")


class AIAgentConfigUpdate(BaseModel):
    """更新 AI Agent 配置"""
    llm_config_id: Optional[int] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    proxy: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[str] = None
    max_tokens: Optional[int] = None
    top_p: Optional[str] = None
    is_enabled: Optional[bool] = None
    enable_tools: Optional[bool] = None
    enable_streaming: Optional[bool] = None
    system_prompt: Optional[str] = None


class AIAgentConfigResponse(BaseResponseSchema):
    """AI Agent 配置响应"""
    id: int
    user_id: int
    llm_config_id: Optional[int]
    llm_config_name: Optional[str] = None
    provider: str
    api_base: Optional[str]
    proxy: Optional[str]
    model: str
    temperature: str
    max_tokens: int
    top_p: str
    is_enabled: bool
    enable_tools: bool
    enable_streaming: bool
    status: str
    last_test_at: Optional[datetime]
    last_test_result: Optional[str]
    system_prompt: Optional[str]
    # 不返回 api_key


# ===== 对话 =====

class AIConversationCreate(BaseModel):
    """创建对话"""
    title: Optional[str] = Field(default=None, description="对话标题")
    source: str = Field(default="web", description="来源")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram Chat ID")


class AIConversationUpdate(BaseModel):
    """更新对话"""
    title: Optional[str] = None
    status: Optional[str] = None


class AIConversationResponse(BaseResponseSchema):
    """对话响应"""
    id: int
    user_id: int
    title: Optional[str]
    source: str
    telegram_chat_id: Optional[str]
    status: str
    message_count: int
    last_message_at: Optional[datetime]
    context_summary: Optional[str]


class AIConversationListResponse(BaseModel):
    """对话列表响应"""
    items: List[AIConversationResponse]
    total: int
    page: int
    page_size: int


# ===== 消息 =====

class AIMessageCreate(BaseModel):
    """创建消息（用户发送）"""
    content: str = Field(..., description="消息内容")


class AIMessageResponse(BaseResponseSchema):
    """消息响应"""
    id: int
    conversation_id: int
    role: str
    content: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_call_id: Optional[str]
    tool_name: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    model: Optional[str]
    finish_reason: Optional[str]


class AIConversationDetailResponse(AIConversationResponse):
    """对话详情响应（包含消息）"""
    messages: List[AIMessageResponse]


# ===== 聊天请求/响应 =====

class AIChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[int] = Field(default=None, description="对话ID（可选，不传则创建新对话）")
    stream: bool = Field(default=False, description="是否流式输出")


class AIChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: int = Field(..., description="对话ID")
    message_id: int = Field(..., description="消息ID")
    content: str = Field(..., description="AI回复内容")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具调用")
    tool_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具执行结果")
    finish_reason: str = Field(default="stop", description="完成原因")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token使用情况")


class AIChatStreamChunk(BaseModel):
    """流式聊天响应块"""
    conversation_id: int
    content: str
    done: bool = False


# ===== 工具执行 =====

class AIToolExecutionResponse(BaseResponseSchema):
    """工具执行响应"""
    id: int
    message_id: int
    conversation_id: int
    user_id: int
    tool_name: str
    tool_call_id: str
    arguments: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    execution_time_ms: Optional[int]


# ===== 连接测试 =====

class AIConnectionTestRequest(BaseModel):
    """连接测试请求"""
    provider: str = Field(..., description="供应商")
    api_key: str = Field(..., description="API密钥")
    api_base: Optional[str] = Field(default=None, description="API基础URL")
    proxy: Optional[str] = Field(default=None, description="代理")
    model: Optional[str] = Field(default=None, description="模型")


class AIConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str
    latency_ms: int
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


# ===== 供应商信息 =====

class LLMProviderInfo(BaseModel):
    """LLM供应商信息"""
    provider: str
    display_name: str
    models: List[Dict[str, str]]  # [{"id": "glm-4", "name": "GLM-4"}]
    supports_tools: bool = True
    supports_streaming: bool = True


class LLMProvidersResponse(BaseModel):
    """供应商列表响应"""
    providers: List[LLMProviderInfo]
