# -*- coding: utf-8 -*-
"""
MCP API 接口

1. 外部 MCP Server 管理（REST API）
   - 增删改查已配置的外部 MCP Server
   - 测试连接 / 同步工具列表

2. NasFusion MCP Server 对外暴露（MCP 协议端点）
   - GET /mcp/sse     SSE 连接，供 Claude Desktop / Claude Code 等客户端接入
   - POST /mcp/messages  SSE 消息投递
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.services.mcp_service import MCPService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["MCP"])

_bearer = HTTPBearer(auto_error=False)


# ===== Pydantic 请求/响应模型 =====

class MCPServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    transport_type: str = "http"
    url: Optional[str] = None
    command: Optional[str] = None
    command_args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    auth_type: str = "none"
    auth_token: Optional[str] = None
    is_enabled: bool = True


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    command: Optional[str] = None
    command_args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = None
    auth_token: Optional[str] = None
    is_enabled: Optional[bool] = None


class MCPServerResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    transport_type: str
    url: Optional[str] = None
    command: Optional[str] = None
    auth_type: str
    is_enabled: bool
    tools_count: Optional[int] = None
    last_sync_at: Optional[Any] = None
    last_error: Optional[str] = None
    created_at: Any

    model_config = {"from_attributes": True}


# ===== 外部 MCP Server 管理 =====

@router.get("/external-servers", response_model=List[MCPServerResponse])
async def list_external_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户配置的外部 MCP Server 列表"""
    servers = await MCPService.list_servers(db, current_user.id)
    result = []
    for s in servers:
        resp = MCPServerResponse.model_validate(s)
        resp.tools_count = len(s.tools_cache) if s.tools_cache else None
        result.append(resp)
    return result


@router.post(
    "/external-servers",
    response_model=MCPServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_external_server(
    data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加外部 MCP Server"""
    server = await MCPService.create_server(
        db, current_user.id, data.model_dump(exclude_none=True)
    )
    return MCPServerResponse.model_validate(server)


@router.put("/external-servers/{server_id}", response_model=MCPServerResponse)
async def update_external_server(
    server_id: int,
    data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新外部 MCP Server 配置"""
    server = await MCPService.get_server(db, server_id, current_user.id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    server = await MCPService.update_server(db, server, data.model_dump(exclude_none=True))
    return MCPServerResponse.model_validate(server)


@router.delete("/external-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_external_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除外部 MCP Server"""
    server = await MCPService.get_server(db, server_id, current_user.id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    await MCPService.delete_server(db, server)


@router.post("/external-servers/{server_id}/test")
async def test_external_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试外部 MCP Server 连接"""
    server = await MCPService.get_server(db, server_id, current_user.id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return await MCPService.test_server_connection(server)


@router.post("/external-servers/{server_id}/sync")
async def sync_external_server_tools(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """同步外部 MCP Server 工具列表到缓存"""
    server = await MCPService.get_server(db, server_id, current_user.id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    try:
        tools = await MCPService.sync_server_tools(db, server)
        return {"success": True, "tools_count": len(tools), "tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== NasFusion MCP Server 对外暴露 =====

@router.get("/sse")
async def mcp_sse_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """
    MCP SSE 连接端点

    外部 MCP 客户端（Claude Desktop、Claude Code）通过此端点接入 NasFusion。

    认证：Authorization: Bearer <JWT Token>
    也支持 query 参数：?token=<JWT Token>（部分客户端不支持自定义 Header）
    """
    from app.core.database import async_session_local
    from app.mcp.context import set_user_context
    from app.mcp.server import handle_sse_connection
    from app.utils.security import decode_access_token

    # 获取 token（优先 Header，其次 query param）
    raw_token = None
    if credentials:
        raw_token = credentials.credentials
    if not raw_token:
        raw_token = request.query_params.get("token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
        )

    payload = decode_access_token(raw_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    # 为 SSE 长连接创建独立的 DB session（不依赖请求生命周期）
    async with async_session_local() as db:
        async with set_user_context(user_id=user_id, db=db):
            await handle_sse_connection(request.scope, request.receive, request._send)

    return Response()


@router.post("/messages")
async def mcp_messages_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """
    MCP 消息投递端点（SSE 传输层使用）

    由 SSE 客户端在发送请求时调用，不需要直接访问。
    """
    from app.core.database import async_session_local
    from app.mcp.context import set_user_context
    from app.mcp.server import handle_sse_message
    from app.utils.security import decode_access_token

    # 同 SSE 端点的认证逻辑
    raw_token = None
    if credentials:
        raw_token = credentials.credentials
    if not raw_token:
        raw_token = request.query_params.get("token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
        )

    payload = decode_access_token(raw_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    async with async_session_local() as db:
        async with set_user_context(user_id=user_id, db=db):
            await handle_sse_message(request.scope, request.receive, request._send)

    return Response()
