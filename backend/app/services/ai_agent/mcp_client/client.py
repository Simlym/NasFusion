# -*- coding: utf-8 -*-
"""
MCP 客户端（聚合层）

为 AIAgentService 提供统一的工具接口：
- 内部工具：直接调用 ToolRegistry（无网络开销）
- 外部工具：通过 MCP 协议调用远程 MCP Server

AgentService 通过此客户端完全替代原有的直接 ToolRegistry 调用。
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.base import ToolDefinition

logger = logging.getLogger(__name__)

# 外部工具名称分隔符：server_name:tool_name
EXTERNAL_TOOL_SEPARATOR = ":"


class MCPClient:
    """
    MCP 客户端（内部 + 外部工具聚合）

    - list_tools(): 返回内部工具 + 所有已启用外部 MCP Server 的工具
    - call_tool(): 自动路由到内部工具或外部 MCP Server
    """

    async def list_tools(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> List[ToolDefinition]:
        """
        获取所有可用工具定义

        Returns:
            ToolDefinition 列表，可直接传给 LLM 的 Function Calling 接口
        """
        from app.services.ai_agent import tools  # noqa: F401 触发工具注册
        from app.services.ai_agent import skills  # noqa: F401 触发 Skill 注册
        from app.services.ai_agent.tool_registry import ToolRegistry

        # 内部工具（ToolRegistry，含 Skills）
        internal = ToolRegistry.get_tool_definitions()

        # 外部 MCP Server 工具
        external = await self._get_external_tools(db, user_id)

        return internal + external

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        db: AsyncSession,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        执行工具调用

        自动路由：
        - 名称含 ":" 前缀 → 外部 MCP Server
        - 否则 → 内部 ToolRegistry
        """
        from app.services.ai_agent import tools  # noqa: F401
        from app.services.ai_agent import skills  # noqa: F401
        from app.services.ai_agent.tool_registry import ToolRegistry

        # 外部工具（格式：server_name:tool_name）
        if EXTERNAL_TOOL_SEPARATOR in name:
            result = await self._call_external_tool(name, arguments, db, user_id)
            if result is not None:
                return result

        # 内部工具
        return await ToolRegistry.execute_tool(name, db, user_id, arguments)

    # ===== 外部工具 =====

    async def _get_external_tools(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> List[ToolDefinition]:
        """获取所有已启用外部 MCP Server 的工具"""
        try:
            from app.services.ai_agent.mcp_client.service import MCPService
            servers = await MCPService.list_enabled_servers(db, user_id)
        except Exception as e:
            logger.warning(f"获取外部 MCP Server 列表失败: {e}")
            return []

        all_tools: List[ToolDefinition] = []
        for server in servers:
            try:
                tools = await self._fetch_server_tools(server, db)
                all_tools.extend(tools)
            except Exception as e:
                logger.warning(f"获取外部 MCP Server [{server.name}] 工具失败: {e}")

        return all_tools

    async def _fetch_server_tools(self, server, db: AsyncSession) -> List[ToolDefinition]:
        """
        从单个外部 MCP Server 获取工具列表

        优先使用缓存，缓存为空时从远程获取并保存。
        """
        from app.services.ai_agent.mcp_client.service import MCPService

        # 优先使用缓存
        if server.tools_cache:
            return [
                ToolDefinition(
                    name=f"{server.name}{EXTERNAL_TOOL_SEPARATOR}{t['name']}",
                    description=f"[{server.name}] {t['description']}",
                    parameters=t.get("inputSchema", {}),
                )
                for t in server.tools_cache
            ]

        # 缓存为空，从远程获取并保存
        try:
            await MCPService.sync_server_tools(db, server)
            if server.tools_cache:
                return [
                    ToolDefinition(
                        name=f"{server.name}{EXTERNAL_TOOL_SEPARATOR}{t['name']}",
                        description=f"[{server.name}] {t['description']}",
                        parameters=t.get("inputSchema", {}),
                    )
                    for t in server.tools_cache
                ]
        except Exception as e:
            logger.warning(f"远程获取工具失败 [{server.name}]: {e}")

        return []

    async def _call_external_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        db: AsyncSession,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:
        """调用外部 MCP Server 的工具"""
        server_name, tool_name = name.split(EXTERNAL_TOOL_SEPARATOR, 1)

        try:
            from app.services.ai_agent.mcp_client.service import MCPService
            server = await MCPService.get_server_by_name(db, user_id, server_name)
        except Exception as e:
            logger.warning(f"查找外部 MCP Server [{server_name}] 失败: {e}")
            return {"success": False, "error": f"外部 MCP Server [{server_name}] 查找失败"}

        if not server or not server.is_enabled:
            return {"success": False, "error": f"外部 MCP Server [{server_name}] 不存在或未启用"}

        try:
            from app.services.ai_agent.mcp_client.service import MCPService
            return await MCPService.call_external_tool(server, tool_name, arguments)
        except Exception as e:
            logger.exception(f"调用外部工具失败 [{name}]")
            return {"success": False, "error": str(e)}


# 全局单例
mcp_client = MCPClient()
