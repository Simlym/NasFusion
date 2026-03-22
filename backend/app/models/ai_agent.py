# -*- coding: utf-8 -*-
"""
AI Agent 相关数据库模型
"""
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.core.db_types import TZDateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.utils.timezone import now


class AIAgentConfig(BaseModel):
    """
    AI Agent 配置表

    存储 LLM 供应商配置、模型设置等
    """

    __tablename__ = "ai_agent_configs"

    # 用户关联
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )

    # 供应商配置
    provider = Column(
        String(50),
        nullable=False,
        default="zhipu",
        comment="LLM供应商: zhipu, openai, deepseek等",
    )
    api_key = Column(
        Text,
        nullable=True,
        comment="API密钥（加密存储）",
    )
    api_base = Column(
        String(255),
        nullable=True,
        comment="API基础URL（可选）",
    )
    proxy = Column(
        String(255),
        nullable=True,
        comment="代理服务器URL",
    )

    # 模型配置
    model = Column(
        String(100),
        nullable=False,
        default="glm-4-flash",
        comment="使用的模型",
    )
    temperature = Column(
        String(10),
        nullable=False,
        default="0.7",
        comment="温度参数",
    )
    max_tokens = Column(
        Integer,
        nullable=False,
        default=2048,
        comment="最大Token数",
    )
    top_p = Column(
        String(10),
        nullable=False,
        default="0.9",
        comment="Top-P参数",
    )

    # 功能开关
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否启用",
    )
    enable_tools = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用工具调用",
    )
    enable_streaming = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用流式输出",
    )

    # 状态
    status = Column(
        String(20),
        nullable=False,
        default="disabled",
        comment="状态: enabled, disabled, error",
    )
    last_test_at = Column(
        TZDateTime(),
        nullable=True,
        comment="最后测试时间",
    )
    last_test_result = Column(
        Text,
        nullable=True,
        comment="最后测试结果",
    )

    # 系统提示词（可自定义）
    system_prompt = Column(
        Text,
        nullable=True,
        comment="自定义系统提示词",
    )

    # 关系
    user = relationship("User", backref="ai_agent_configs")


class AIConversation(BaseModel):
    """
    AI 对话表

    存储用户与 AI 的对话会话
    """

    __tablename__ = "ai_conversations"

    # 用户关联
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )

    # 对话信息
    title = Column(
        String(255),
        nullable=True,
        comment="对话标题（自动生成或用户设置）",
    )
    source = Column(
        String(20),
        nullable=False,
        default="web",
        comment="来源: web, telegram, api",
    )

    # Telegram 相关
    telegram_chat_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Telegram Chat ID",
    )

    # 状态
    status = Column(
        String(20),
        nullable=False,
        default="active",
        comment="状态: active, archived, deleted",
    )
    message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="消息数量",
    )
    last_message_at = Column(
        TZDateTime(),
        nullable=True,
        comment="最后消息时间",
    )

    # 上下文摘要（用于长对话）
    context_summary = Column(
        Text,
        nullable=True,
        comment="上下文摘要",
    )

    # 关系
    user = relationship("User", backref="ai_conversations")
    messages = relationship(
        "AIMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at",
    )


class AIMessage(BaseModel):
    """
    AI 消息表

    存储对话中的每条消息
    """

    __tablename__ = "ai_messages"

    # 对话关联
    conversation_id = Column(
        Integer,
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="对话ID",
    )

    # 消息内容
    role = Column(
        String(20),
        nullable=False,
        comment="角色: system, user, assistant, tool",
    )
    content = Column(
        Text,
        nullable=True,
        comment="消息内容",
    )

    # 工具调用相关
    tool_calls = Column(
        JSON,
        nullable=True,
        comment="工具调用列表（JSON格式）",
    )
    tool_call_id = Column(
        String(50),
        nullable=True,
        comment="工具调用ID（当role=tool时）",
    )
    tool_name = Column(
        String(50),
        nullable=True,
        comment="工具名称（当role=tool时）",
    )

    # Token 统计
    prompt_tokens = Column(
        Integer,
        nullable=True,
        comment="输入Token数",
    )
    completion_tokens = Column(
        Integer,
        nullable=True,
        comment="输出Token数",
    )

    # 元数据
    model = Column(
        String(100),
        nullable=True,
        comment="使用的模型",
    )
    finish_reason = Column(
        String(20),
        nullable=True,
        comment="完成原因: stop, tool_calls, length",
    )

    # 关系
    conversation = relationship("AIConversation", back_populates="messages")


class AIToolExecution(BaseModel):
    """
    AI 工具执行记录表

    记录 Agent 调用工具的历史
    """

    __tablename__ = "ai_tool_executions"

    # 关联
    message_id = Column(
        Integer,
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="消息ID",
    )
    conversation_id = Column(
        Integer,
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="对话ID",
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )

    # 工具信息
    tool_name = Column(
        String(50),
        nullable=False,
        comment="工具名称",
    )
    tool_call_id = Column(
        String(50),
        nullable=False,
        comment="工具调用ID",
    )

    # 参数和结果
    arguments = Column(
        JSON,
        nullable=True,
        comment="调用参数（JSON格式）",
    )
    result = Column(
        JSON,
        nullable=True,
        comment="执行结果（JSON格式）",
    )

    # 执行状态
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态: pending, running, completed, failed",
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    execution_time_ms = Column(
        Integer,
        nullable=True,
        comment="执行时间（毫秒）",
    )

    # 关系
    user = relationship("User")
