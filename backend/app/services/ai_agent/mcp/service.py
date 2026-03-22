# -*- coding: utf-8 -*-
"""
MCP Service

管理外部 MCP Server 的注册、工具同步和调用。
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_server import MCPExternalServer
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class MCPService:

    # ===== 外部 Server CRUD =====

    @staticmethod
    async def list_servers(db: AsyncSession, user_id: int) -> List[MCPExternalServer]:
        """列出用户所有外部 MCP Server"""
        result = await db.execute(
            select(MCPExternalServer)
            .where(MCPExternalServer.user_id == user_id)
            .order_by(MCPExternalServer.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_enabled_servers(db: AsyncSession, user_id: int) -> List[MCPExternalServer]:
        """列出用户已启用的外部 MCP Server"""
        result = await db.execute(
            select(MCPExternalServer)
            .where(
                MCPExternalServer.user_id == user_id,
                MCPExternalServer.is_enabled == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_server(
        db: AsyncSession,
        server_id: int,
        user_id: int,
    ) -> Optional[MCPExternalServer]:
        """获取指定外部 MCP Server"""
        result = await db.execute(
            select(MCPExternalServer).where(
                MCPExternalServer.id == server_id,
                MCPExternalServer.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_server_by_name(
        db: AsyncSession,
        user_id: int,
        name: str,
    ) -> Optional[MCPExternalServer]:
        """按名称获取外部 MCP Server"""
        result = await db.execute(
            select(MCPExternalServer).where(
                MCPExternalServer.user_id == user_id,
                MCPExternalServer.name == name,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_server(
        db: AsyncSession,
        user_id: int,
        data: Dict[str, Any],
    ) -> MCPExternalServer:
        """创建外部 MCP Server 配置"""
        server = MCPExternalServer(user_id=user_id, **data)
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return server

    @staticmethod
    async def update_server(
        db: AsyncSession,
        server: MCPExternalServer,
        data: Dict[str, Any],
    ) -> MCPExternalServer:
        """更新外部 MCP Server 配置"""
        for key, value in data.items():
            if hasattr(server, key):
                setattr(server, key, value)
        await db.commit()
        await db.refresh(server)
        return server

    @staticmethod
    async def delete_server(db: AsyncSession, server: MCPExternalServer) -> None:
        """删除外部 MCP Server 配置"""
        await db.delete(server)
        await db.commit()

    # ===== 工具获取与调用 =====

    @staticmethod
    async def fetch_server_tools(server: MCPExternalServer) -> list:
        """连接外部 MCP Server，获取工具列表（mcp.types.Tool 列表）"""
        if server.transport_type == "http":
            return await MCPService._fetch_http_tools(server)
        logger.warning(f"暂不支持的传输类型: {server.transport_type}")
        return []

    @staticmethod
    async def _fetch_http_tools(server: MCPExternalServer) -> list:
        """通过 HTTP+SSE 获取工具列表"""
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client

        headers = MCPService._build_auth_headers(server)

        async with sse_client(server.url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    @staticmethod
    async def call_external_tool(
        server: MCPExternalServer,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """调用外部 MCP Server 的工具"""
        if server.transport_type == "http":
            return await MCPService._call_http_tool(server, tool_name, arguments)
        return {"success": False, "error": f"不支持的传输类型: {server.transport_type}"}

    @staticmethod
    async def _call_http_tool(
        server: MCPExternalServer,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """通过 HTTP+SSE 调用工具"""
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client

        headers = MCPService._build_auth_headers(server)

        try:
            async with sse_client(server.url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    call_result = await session.call_tool(tool_name, arguments)

                    # 将 MCP CallToolResult 转换为内部 dict 格式
                    if call_result.content:
                        content = call_result.content[0]
                        if hasattr(content, "text"):
                            try:
                                return json.loads(content.text)
                            except (json.JSONDecodeError, ValueError):
                                return {"success": True, "result": content.text}

                    return {"success": True, "result": None}

        except Exception as e:
            logger.exception(f"调用外部工具失败 [{server.name}:{tool_name}]")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def sync_server_tools(
        db: AsyncSession,
        server: MCPExternalServer,
    ) -> List[dict]:
        """
        同步外部 MCP Server 工具列表到缓存

        Returns:
            工具列表（dict 格式）
        """
        try:
            tools = await MCPService.fetch_server_tools(server)
            tools_cache = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema or {},
                }
                for t in tools
            ]
            server.tools_cache = tools_cache
            server.last_sync_at = now()
            server.last_error = None
            await db.commit()
            return tools_cache
        except Exception as e:
            server.last_error = str(e)
            await db.commit()
            raise

    @staticmethod
    async def test_server_connection(server: MCPExternalServer) -> Dict[str, Any]:
        """测试外部 MCP Server 连接"""
        try:
            tools = await MCPService.fetch_server_tools(server)
            return {
                "success": True,
                "message": f"连接成功，发现 {len(tools)} 个工具",
                "tools_count": len(tools),
                "tools": [t.name for t in tools],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
            }

    @staticmethod
    def _build_auth_headers(server: MCPExternalServer) -> dict:
        """构建认证请求头"""
        headers = {}
        if server.auth_type == "bearer" and server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"
        elif server.auth_type == "api_key" and server.auth_token:
            headers["X-API-Key"] = server.auth_token
        return headers
