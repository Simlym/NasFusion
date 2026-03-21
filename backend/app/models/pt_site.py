"""
PT站点相关数据模型
"""
from sqlalchemy import Boolean, Column, Integer, String, Text

from app.models.base import BaseModel
from app.core.json_types import JSON, TZDateTime


class PTSite(BaseModel):
    """PT站点配置表"""

    __tablename__ = "pt_sites"

    # 预设配置ID（如 hdsky, mteam），用于快速加载默认配置
    preset_id = Column(String(50), nullable=True, index=True, comment="站点预设ID")

    name = Column(String(100), nullable=False, comment="站点名称")
    type = Column(String(50), nullable=False, comment="站点类型（对应爬虫适配器）")
    domain = Column(String(255), unique=True, nullable=False, index=True, comment="站点域名")
    base_url = Column(String(500), nullable=False, comment="完整URL")

    # 认证信息
    auth_type = Column(
        String(50), nullable=False, comment="认证方式: cookie/passkey/user_pass"
    )
    auth_cookie = Column(Text, nullable=True, comment="Cookie（加密存储）")
    auth_passkey = Column(String(255), nullable=True, comment="Passkey（加密存储）")
    auth_username = Column(String(255), nullable=True, comment="用户名（加密存储）")
    auth_password = Column(String(255), nullable=True, comment="密码（加密存储）")
    cookie_expire_at = Column(TZDateTime(), nullable=True, comment="Cookie过期时间")

    # 代理和能力配置
    proxy_config = Column(JSON, nullable=True, comment="代理配置")
    capabilities = Column(JSON, nullable=True, comment="站点能力配置")

    # 同步配置
    sync_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用同步")
    sync_strategy = Column(
        String(50), nullable=True, comment="同步策略: time_based/page_based/id_based"
    )
    sync_interval = Column(Integer, nullable=True, comment="同步间隔（分钟）")
    sync_config = Column(JSON, nullable=True, comment="同步详细配置")
    last_sync_at = Column(TZDateTime(), nullable=True, comment="最后同步时间")
    last_sync_status = Column(
        String(50), nullable=True, comment="最后同步状态: success/failed/running"
    )
    last_sync_error = Column(Text, nullable=True, comment="最后同步错误信息")

    # 限流配置
    request_interval = Column(Integer, nullable=True, comment="请求间隔（秒）")
    max_requests_per_day = Column(Integer, nullable=True, comment="每日最大请求数")
    daily_requests_used = Column(Integer, default=0, nullable=False, comment="今日已用请求数")

    # 站点状态
    status = Column(String(50), default="active", nullable=False, comment="站点状态: active/inactive/error")
    health_check_at = Column(TZDateTime(), nullable=True, comment="最后健康检查时间")
    health_status = Column(String(50), nullable=True, comment="健康状态: healthy/unhealthy")

    # 站点用户信息（JSON格式存储用户名、等级、数据量等）
    user_profile = Column(JSON, nullable=True, comment="站点用户信息")

    # 统计信息
    total_resources = Column(Integer, default=0, nullable=False, comment="总资源数")
    total_synced = Column(Integer, default=0, nullable=False, comment="已同步数")

    def __repr__(self):
        return f"<PTSite(id={self.id}, name={self.name}, domain={self.domain})>"

    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.health_status == "healthy"

    @property
    def is_sync_enabled(self) -> bool:
        """是否启用同步"""
        return self.sync_enabled and self.status == "active"
