# -*- coding: utf-8 -*-
"""
媒体服务器配置模型（通用：Jellyfin/Emby/Plex）
"""
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.json_types import JSON, TZDateTime


class MediaServerConfig(Base):
    """媒体服务器配置表（通用：Jellyfin/Emby/Plex）"""

    __tablename__ = "media_server_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 用户关联
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")

    # 服务器类型和基础信息
    type = Column(String(50), nullable=False, index=True, comment="服务器类型：jellyfin/emby/plex")
    name = Column(String(100), nullable=False, comment="配置名称（用户自定义）")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否默认服务器")

    # 连接信息
    host = Column(String(255), nullable=False, comment="服务器地址")
    port = Column(Integer, nullable=False, comment="端口号")
    use_ssl = Column(Boolean, default=False, nullable=False, comment="是否使用SSL/HTTPS")

    # 认证信息（加密存储）
    api_key = Column(Text, nullable=True, comment="API Key（加密存储，Jellyfin/Emby使用）")
    token = Column(Text, nullable=True, comment="访问令牌（加密存储，Plex使用）")
    username = Column(String(255), nullable=True, comment="用户名（某些场景需要）")
    password = Column(Text, nullable=True, comment="密码（加密存储）")

    # 服务器特定配置（JSON格式）
    server_config = Column(
        JSON,
        nullable=True,
        comment="""特定服务器的额外配置，JSON格式：
        {
          "server_user_id": "123456",  # 媒体服务器的用户ID（用于观看历史同步）
          "library_mappings": {         # 媒体库映射关系
            "library_id_1": "Movies",
            "library_id_2": "TV Shows"
          }
        }
        """,
    )

    # 功能开关
    auto_refresh_library = Column(Boolean, default=True, nullable=False, comment="文件整理后自动刷新媒体库")
    sync_watch_history = Column(Boolean, default=True, nullable=False, comment="同步观看历史")
    watch_history_sync_interval = Column(Integer, default=60, nullable=False, comment="观看历史同步间隔（分钟）")

    # 媒体库路径映射（服务器路径 → NasFusion路径）
    library_path_mappings = Column(
        JSON,
        nullable=True,
        comment="""路径映射配置，JSON格式：
        [
          {
            "server_path": "/media/movies",
            "local_path": "./data/media/Movies"
          },
          {
            "server_path": "/media/tv",
            "local_path": "./data/media/TV Shows"
          }
        ]
        """,
    )

    # 状态信息
    status = Column(String(50), default="offline", nullable=False, index=True, comment="状态：online/offline/error")
    last_check_at = Column(TZDateTime(), nullable=True, comment="最后连接检查时间")
    last_sync_at = Column(TZDateTime(), nullable=True, comment="最后同步观看历史时间")
    last_error = Column(Text, nullable=True, comment="最后错误信息")

    # 时间戳
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 索引和约束
    __table_args__ = (
        Index("idx_media_server_configs_type", "type"),
        Index("idx_media_server_configs_user_type", "user_id", "type"),
        Index("idx_media_server_configs_status", "status"),
        CheckConstraint(
            "type IN ('jellyfin', 'emby', 'plex')",
            name="check_media_server_type",
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'error')",
            name="check_media_server_status",
        ),
    )

    def __repr__(self):
        return f"<MediaServerConfig(name={self.name}, type={self.type}, status={self.status})>"
