"""
登录历史相关 Schemas
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginHistoryResponse(BaseModel):
    """登录历史记录响应"""

    id: int
    user_id: int
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None
    login_status: str = Field(..., description="登录状态: success/failed/locked")
    failure_reason: Optional[str] = None
    login_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class LoginHistoryListResponse(BaseModel):
    """登录历史列表响应"""

    items: list[LoginHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
