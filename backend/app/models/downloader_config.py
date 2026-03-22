# -*- coding: utf-8 -*-
"""
下载器配置模型
"""
from sqlalchemy import Boolean, Column, Integer, String, Text, Index, CheckConstraint
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.db_types import JSON, TZDateTime


class DownloaderConfig(Base):
    """下载器配置表"""

    __tablename__ = "downloader_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 基础信息
    name = Column(String(100), nullable=False, unique=True, comment="下载器名称（唯一，如：qBittorrent-本地）")
    type = Column(String(50), nullable=False, comment="下载器类型：qbittorrent/transmission/synology_ds")
    is_default = Column(Boolean, default=False, nullable=False, index=True, comment="是否默认下载器")
    is_enabled = Column(Boolean, default=True, nullable=False, index=True, comment="是否启用")

    # 连接信息
    host = Column(String(255), nullable=False, comment="主机地址（IP或域名）")
    port = Column(Integer, nullable=False, comment="端口号")
    username = Column(String(255), nullable=True, comment="用户名（加密存储）")
    password = Column(Text, nullable=True, comment="密码（加密存储）")
    use_ssl = Column(Boolean, default=False, nullable=False, comment="是否使用SSL/HTTPS")

    # 分类路径配置（已废弃，使用 storage_mounts 表代替）
    category_paths = Column(
        JSON,
        nullable=True,
        comment="[已废弃] 分类路径映射，已由 storage_mounts 表替代，保留仅用于数据迁移",
    )

    # HR处理策略
    hr_strategy = Column(
        String(50),
        default="auto_limit",
        nullable=False,
        comment="HR处理策略：none/auto_limit/manual",
    )

    # 高级配置
    max_concurrent_downloads = Column(Integer, default=5, nullable=True, comment="最大并发下载数")
    download_speed_limit = Column(Integer, default=0, nullable=True, comment="下载速度限制（KB/s，0为不限制）")
    upload_speed_limit = Column(Integer, default=0, nullable=True, comment="上传速度限制（KB/s，0为不限制）")

    # 状态信息
    status = Column(String(50), default="offline", nullable=False, index=True, comment="状态：online/offline/error")
    last_check_at = Column(TZDateTime(), nullable=True, comment="最后检查时间")
    last_error = Column(Text, nullable=True, comment="最后错误信息")

    # 创建和更新时间
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 索引和约束
    __table_args__ = (
        Index("idx_downloader_configs_type", "type"),
        Index("idx_downloader_configs_is_default", "is_default"),
        Index("idx_downloader_configs_is_enabled", "is_enabled"),
        Index("idx_downloader_configs_status", "status"),
        CheckConstraint(
            "type IN ('qbittorrent', 'transmission', 'synology_ds')",
            name="check_downloader_type",
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'error')",
            name="check_downloader_status",
        ),
        CheckConstraint(
            "hr_strategy IN ('none', 'auto_limit', 'manual')",
            name="check_hr_strategy",
        ),
    )

    def __repr__(self):
        return f"<DownloaderConfig(name={self.name}, type={self.type}, status={self.status})>"
