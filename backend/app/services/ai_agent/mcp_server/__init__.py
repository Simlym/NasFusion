# -*- coding: utf-8 -*-
"""
MCP Server 子模块

将 NasFusion 内部工具暴露为标准 MCP Server，
供外部 MCP 客户端（Claude Desktop、Claude Code 等）接入。
"""
from app.services.ai_agent.mcp_server.server import (
    handle_sse_connection,
    handle_sse_message,
    mcp_server,
)

__all__ = [
    "handle_sse_connection",
    "handle_sse_message",
    "mcp_server",
]
