# -*- coding: utf-8 -*-
"""
MCP Client 子模块

调用外部 MCP Server 扩展 AI Agent 能力，
同时聚合内部工具，为 AIAgentService 提供统一的工具接口。
"""
from app.services.ai_agent.mcp_client.client import MCPClient, mcp_client
from app.services.ai_agent.mcp_client.service import MCPService

__all__ = [
    "MCPClient",
    "mcp_client",
    "MCPService",
]
