# -*- coding: utf-8 -*-
"""MCP 相关 Pydantic 模型"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
