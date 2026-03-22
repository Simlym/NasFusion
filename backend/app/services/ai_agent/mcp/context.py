# -*- coding: utf-8 -*-
"""
MCP 用户上下文注入

通过 ContextVar 将 user_id 和 db session 注入到 MCP 工具调用中，
解决 MCP 无状态协议与工具需要用户上下文之间的矛盾。
"""
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

_current_user_id: ContextVar[Optional[int]] = ContextVar("mcp_user_id", default=None)
_current_db: ContextVar[Optional[AsyncSession]] = ContextVar("mcp_db", default=None)


@dataclass
class UserContext:
    """当前请求的用户上下文"""
    user_id: int
    db: AsyncSession


def get_user_context() -> UserContext:
    """
    获取当前用户上下文（在工具执行时调用）

    Raises:
        RuntimeError: 未设置用户上下文时抛出
    """
    user_id = _current_user_id.get()
    db = _current_db.get()
    if user_id is None or db is None:
        raise RuntimeError("用户上下文未设置，请确保在正确的调用链中使用")
    return UserContext(user_id=user_id, db=db)


class set_user_context:
    """
    异步上下文管理器：在工具执行期间设置用户上下文

    用法:
        async with set_user_context(user_id=1, db=db_session):
            await some_tool()
    """

    def __init__(self, user_id: int, db: AsyncSession):
        self.user_id = user_id
        self.db = db
        self._token_uid = None
        self._token_db = None

    async def __aenter__(self):
        self._token_uid = _current_user_id.set(self.user_id)
        self._token_db = _current_db.set(self.db)
        return self

    async def __aexit__(self, *args):
        if self._token_uid is not None:
            _current_user_id.reset(self._token_uid)
        if self._token_db is not None:
            _current_db.reset(self._token_db)
