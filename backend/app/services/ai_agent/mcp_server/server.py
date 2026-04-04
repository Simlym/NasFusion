# -*- coding: utf-8 -*-
"""
NasFusion MCP Server

将内部 ToolRegistry 的所有工具暴露为标准 MCP Server，
支持外部 MCP 客户端（Claude Desktop、Claude Code 等）通过 SSE 连接。

传输协议：HTTP + SSE（Server-Sent Events）
认证方式：JWT Bearer Token（与现有 API 统一）
"""
import json
import logging
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from app.services.ai_agent.context import get_user_context

logger = logging.getLogger(__name__)

# NasFusion MCP Server 实例
mcp_server = Server("nasfusion")

# SSE 传输层（路径与 FastAPI 路由对应）
_sse_transport = SseServerTransport("/api/v1/mcp/messages")


def _ensure_tools_registered():
    """确保所有工具已通过 @register_tool 注册到 ToolRegistry"""
    from app.services.ai_agent import tools  # noqa: F401 触发工具注册


# ===== Tools =====

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出所有可用工具（映射自 ToolRegistry）"""
    _ensure_tools_registered()
    from app.services.ai_agent.tool_registry import ToolRegistry

    return [
        types.Tool(
            name=tc.name,
            description=tc.description,
            inputSchema=tc.parameters,
        )
        for tc in ToolRegistry.get_all_tools().values()
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None,
) -> list[types.TextContent]:
    """
    执行工具调用

    从 ContextVar 中获取用户上下文（user_id + db），
    委托给 ToolRegistry 执行实际逻辑。
    """
    _ensure_tools_registered()
    from app.services.ai_agent.tool_registry import ToolRegistry

    ctx = get_user_context()
    result = await ToolRegistry.execute_tool(
        name,
        ctx.db,
        ctx.user_id,
        arguments or {},
    )

    # 每次工具调用后提交事务，确保写操作持久化
    try:
        await ctx.db.commit()
    except Exception:
        await ctx.db.rollback()

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


# ===== Resources =====

@mcp_server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    列出所有可用资源
    
    外部 MCP Client 可以读取这些资源了解 NasFusion 的状态。
    """
    from app.services.ai_agent.mcp_server.resources import MCPResourceProvider

    resources = MCPResourceProvider.list_resources()
    return [
        types.Resource(
            uri=r["uri"],
            name=r["name"],
            description=r["description"],
            mimeType=r["mimeType"],
        )
        for r in resources
    ]


@mcp_server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """
    读取资源内容
    
    Args:
        uri: 资源 URI，如 nasfusion://downloads/pending
        
    Returns:
        资源内容（JSON 字符串）
    """
    from app.services.ai_agent.mcp_server.resources import MCPResourceProvider

    ctx = get_user_context()
    content = await MCPResourceProvider.read_resource(ctx.db, ctx.user_id, uri)
    
    if content is None:
        raise ValueError(f"未知资源: {uri}")
    
    return content


# ===== Prompts =====

@mcp_server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    列出所有可用提示词
    
    外部 MCP Client 可以使用这些预设的角色提示词。
    """
    from app.services.ai_agent.mcp_server.prompts import MCPPromptProvider

    prompts = MCPPromptProvider.list_prompts()
    return [
        types.Prompt(
            name=p["name"],
            description=p["description"],
        )
        for p in prompts
    ]


@mcp_server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict | None = None) -> types.GetPromptResult:
    """
    获取提示词内容
    
    Args:
        name: 提示词名称
        arguments: 可选的参数
        
    Returns:
        提示词内容
    """
    from app.services.ai_agent.mcp_server.prompts import MCPPromptProvider

    prompt_data = MCPPromptProvider.get_prompt(name, arguments)
    
    if prompt_data is None:
        raise ValueError(f"未知提示词: {name}")
    
    # 转换为 MCP Message 类型
    messages = []
    for msg in prompt_data["messages"]:
        messages.append(
            types.PromptMessage(
                role=msg["role"],
                content=types.TextContent(type="text", text=msg["content"]),
            )
        )
    
    return types.GetPromptResult(
        description=prompt_data["description"],
        messages=messages,
    )


# ===== SSE Connection Handlers =====

async def handle_sse_connection(scope, receive, send) -> None:
    """
    处理外部 MCP 客户端的 SSE 连接

    调用前需通过 set_user_context 设置好用户上下文。
    """
    async with _sse_transport.connect_sse(scope, receive, send) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


async def handle_sse_message(scope, receive, send) -> None:
    """处理 SSE 消息投递（MCP POST /messages 端点）"""
    await _sse_transport.handle_post_message(scope, receive, send)
