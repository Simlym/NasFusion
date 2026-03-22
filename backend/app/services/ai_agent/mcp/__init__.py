# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) 子模块

对外暴露 NasFusion 工具为 MCP Server，
同时支持接入外部 MCP Server 扩展 AI Agent 能力。
"""
from app.services.ai_agent.mcp.client import MCPClient, mcp_client
from app.services.ai_agent.mcp.context import UserContext, get_user_context, set_user_context

__all__ = [
    "MCPClient",
    "mcp_client",
    "UserContext",
    "get_user_context",
    "set_user_context",
]
