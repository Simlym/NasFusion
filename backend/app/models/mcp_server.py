# -*- coding: utf-8 -*-
"""
外部 MCP Server 配置模型

存储用户配置的外部 MCP Server 连接信息，
供 AI Agent 在对话时调用外部工具。
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db_types import JSON, TZDateTime
from app.models.base import BaseModel


class MCPExternalServer(BaseModel):
    """外部 MCP Server 配置"""

    __tablename__ = "mcp_external_servers"

    # 所有者
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所有者用户ID",
    )

    # 基本信息
    name = Column(String(100), nullable=False, comment="Server 名称（用作工具前缀，如 filesystem）")
    description = Column(String(500), nullable=True, comment="描述")

    # 连接配置
    transport_type = Column(
        String(20),
        nullable=False,
        default="http",
        comment="传输类型: http / stdio",
    )
    url = Column(String(500), nullable=True, comment="HTTP SSE 连接 URL")
    command = Column(String(500), nullable=True, comment="stdio 启动命令")
    command_args = Column(JSON, nullable=True, comment="stdio 命令参数列表")
    env_vars = Column(JSON, nullable=True, comment="环境变量（stdio 用）")

    # 认证配置
    auth_type = Column(
        String(20),
        nullable=False,
        default="none",
        comment="认证类型: none / bearer / api_key",
    )
    auth_token = Column(Text, nullable=True, comment="认证 Token（建议加密存储）")

    # 状态
    is_enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    tools_cache = Column(JSON, nullable=True, comment="工具列表缓存（定期或手动同步）")
    last_sync_at = Column(TZDateTime(), nullable=True, comment="最后同步时间")
    last_error = Column(Text, nullable=True, comment="最后一次错误信息")

    # 关联
    user = relationship("User", foreign_keys=[user_id])
