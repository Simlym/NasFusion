# -*- coding: utf-8 -*-
"""
AI Agent 服务模块
"""
from app.services.ai_agent.agent_service import AIAgentService
from app.services.ai_agent.tool_registry import (
    BaseTool,
    ToolRegistry,
    register_tool,
)
from app.services.ai_agent.context import (
    UserContext,
    get_user_context,
    set_user_context,
)
from app.services.ai_agent.mcp_client import (
    MCPClient,
    mcp_client,
)

__all__ = [
    "AIAgentService",
    "BaseTool",
    "ToolRegistry",
    "register_tool",
    "MCPClient",
    "mcp_client",
    "UserContext",
    "get_user_context",
    "set_user_context",
]
