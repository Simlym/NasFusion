"""
PT站点相关Schemas
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.constants import (
    AUTH_TYPES,
    SITE_STATUSES,
    SYNC_STRATEGIES,
)


class PTSiteBase(BaseModel):
    """PT站点基础信息"""

    name: str = Field(..., min_length=1, max_length=100, description="站点名称")
    type: str = Field(..., description="站点类型")
    domain: str = Field(..., description="站点域名")
    base_url: str = Field(..., description="完整URL")


class PTSiteCreate(PTSiteBase):
    """创建PT站点"""

    auth_type: str = Field(..., description="认证方式: cookie/passkey/user_pass")
    auth_cookie: Optional[str] = Field(None, description="Cookie")
    auth_passkey: Optional[str] = Field(None, description="Passkey")
    auth_username: Optional[str] = Field(None, description="用户名")
    auth_password: Optional[str] = Field(None, description="密码")
    cookie_expire_at: Optional[datetime] = Field(None, description="Cookie过期时间")
    proxy_config: Optional[Dict[str, Any]] = Field(None, description="代理配置")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="站点能力配置")
    sync_enabled: bool = Field(default=True, description="是否启用同步")
    sync_strategy: Optional[str] = Field(None, description="同步策略")
    sync_interval: Optional[int] = Field(None, ge=1, description="同步间隔（分钟）")
    sync_config: Optional[Dict[str, Any]] = Field(None, description="同步详细配置")
    request_interval: Optional[int] = Field(None, ge=1, description="请求间隔（秒）")
    max_requests_per_day: Optional[int] = Field(None, ge=0, description="每日最大请求数")

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """验证认证方式"""
        if v not in AUTH_TYPES:
            raise ValueError(f"认证方式必须是: {', '.join(AUTH_TYPES)}之一")
        return v

    @field_validator("sync_strategy")
    @classmethod
    def validate_sync_strategy(cls, v: Optional[str]) -> Optional[str]:
        """验证同步策略"""
        if v is not None and v not in SYNC_STRATEGIES:
            raise ValueError(f"同步策略必须是: {', '.join(SYNC_STRATEGIES)}之一")
        return v


class PTSiteCreateFromPreset(BaseModel):
    """从预设创建PT站点（简化配置）"""

    preset_id: str = Field(..., description="站点预设ID（如 hdsky, mteam）")

    # 必填认证信息
    auth_cookie: Optional[str] = Field(None, description="Cookie（NexusPHP站点必填）")
    auth_passkey: Optional[str] = Field(None, description="Passkey（用于下载种子）")

    # 可选覆盖配置
    name: Optional[str] = Field(None, max_length=100, description="自定义站点名称（默认使用预设名称）")
    domain: Optional[str] = Field(None, description="自定义域名（默认使用预设域名）")
    base_url: Optional[str] = Field(None, description="自定义URL（默认使用预设URL）")
    proxy_config: Optional[Dict[str, Any]] = Field(None, description="代理配置")
    sync_enabled: bool = Field(default=True, description="是否启用同步")
    sync_interval: Optional[int] = Field(None, ge=1, description="同步间隔（分钟）")
    request_interval: Optional[int] = Field(None, ge=1, description="请求间隔（秒）")


class PTSiteUpdate(BaseModel):
    """更新PT站点"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = None
    domain: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_cookie: Optional[str] = None
    auth_passkey: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    cookie_expire_at: Optional[datetime] = None
    proxy_config: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    sync_enabled: Optional[bool] = None
    sync_strategy: Optional[str] = None
    sync_interval: Optional[int] = Field(None, ge=1)
    sync_config: Optional[Dict[str, Any]] = None
    request_interval: Optional[int] = Field(None, ge=1)
    max_requests_per_day: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: Optional[str]) -> Optional[str]:
        """验证认证方式"""
        if v is not None and v not in AUTH_TYPES:
            raise ValueError(f"认证方式必须是: {', '.join(AUTH_TYPES)}之一")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证状态"""
        if v is not None and v not in SITE_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(SITE_STATUSES)}之一")
        return v


class PTSiteResponse(PTSiteBase):
    """PT站点响应"""

    id: int
    preset_id: Optional[str] = Field(None, description="站点预设ID")
    auth_type: str
    # 认证信息已设置标志（不返回实际值，仅标识是否已保存）
    has_auth_cookie: bool = Field(default=False, description="是否已设置Cookie")
    has_auth_passkey: bool = Field(default=False, description="是否已设置Passkey")
    has_auth_password: bool = Field(default=False, description="是否已设置密码")
    cookie_expire_at: Optional[datetime]
    proxy_config: Optional[Dict[str, Any]]
    capabilities: Optional[Dict[str, Any]]
    sync_enabled: bool
    sync_strategy: Optional[str]
    sync_interval: Optional[int]
    sync_config: Optional[Dict[str, Any]]
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_error: Optional[str]
    request_interval: Optional[int]
    max_requests_per_day: Optional[int]
    daily_requests_used: int
    status: str
    health_check_at: Optional[datetime]
    health_status: Optional[str]
    user_profile: Optional[Dict[str, Any]] = Field(None, description="站点用户信息")
    total_resources: int
    total_synced: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTSiteListResponse(BaseModel):
    """PT站点列表响应"""

    items: list[PTSiteResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
