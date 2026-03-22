# -*- coding: utf-8 -*-
"""
下载任务模型
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.db_types import JSON, TZDateTime


class DownloadTask(Base):
    """下载任务表"""

    __tablename__ = "download_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 种子标识
    task_hash = Column(String(100), unique=True, nullable=False, index=True, comment="种子哈希（InfoHash），唯一")

    # 关联信息
    pt_resource_id = Column(Integer, ForeignKey("pt_resources.id"), nullable=False, index=True, comment="PT资源ID")
    downloader_config_id = Column(
        Integer, ForeignKey("downloader_configs.id"), nullable=False, index=True, comment="下载器配置ID"
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="创建任务的用户ID")

    # 媒体信息（多态关联设计，与 resource_mappings 保持一致）
    media_type = Column(String(20), nullable=False, index=True, comment="媒体类型：movie/tv/music/book/anime/adult")
    unified_table_name = Column(String(50), nullable=True, index=True, comment="统一资源表名（如 unified_movies, unified_tv_series）")
    unified_resource_id = Column(Integer, nullable=True, index=True, comment="统一资源ID")

    # 下载器信息
    client_type = Column(String(50), nullable=False, comment="下载器类型：qbittorrent/transmission/synology_ds")
    client_task_id = Column(String(100), nullable=True, comment="下载器中的任务ID（如qBittorrent的hash）")
    client_config_snapshot = Column(JSON, nullable=True, comment="下载器配置快照（创建任务时的配置）")

    # 种子文件信息
    torrent_file_path = Column(Text, nullable=True, comment="本地种子文件路径")
    magnet_link = Column(Text, nullable=True, comment="磁力链接")
    torrent_name = Column(String(500), nullable=False, comment="种子名称")

    # 下载路径
    save_path = Column(Text, nullable=False, comment="保存路径（下载目录）")

    # 任务状态
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        comment="状态：pending/downloading/paused/completed/seeding/error/deleted",
    )
    progress = Column(Integer, default=0, nullable=False, comment="下载进度 0-100")

    # 速度和时间
    download_speed = Column(BigInteger, default=0, nullable=True, comment="下载速度（字节/秒）")
    upload_speed = Column(BigInteger, default=0, nullable=True, comment="上传速度（字节/秒）")
    eta = Column(Integer, nullable=True, comment="预计剩余时间（秒）")

    # 大小信息
    total_size = Column(BigInteger, nullable=False, comment="总大小（字节）")
    downloaded_size = Column(BigInteger, default=0, nullable=False, comment="已下载大小（字节）")
    uploaded_size = Column(BigInteger, default=0, nullable=False, comment="已上传大小（字节）")

    # 分享率
    ratio = Column(Numeric(8, 2), default=0.00, nullable=False, comment="分享率")

    # 文件列表
    files = Column(JSON, nullable=True, comment="文件列表，JSON数组")

    # 元数据快照
    metadata_snapshot = Column(JSON, nullable=True, comment="PT资源元数据快照（创建任务时的资源信息）")

    # 自动化配置
    auto_organize = Column(Boolean, default=True, nullable=False, comment="下载完成后是否自动整理")
    organize_config_id = Column(
        Integer, ForeignKey("organize_configs.id"), nullable=True, index=True, comment="整理配置ID（整理规则：文件名模板、NFO生成等）"
    )
    storage_mount_id = Column(
        Integer, ForeignKey("storage_mounts.id"), nullable=True, index=True, comment="存储挂载点ID（最终存储位置）"
    )
    keep_seeding = Column(Boolean, default=True, nullable=False, comment="是否保持做种")
    seeding_time_limit = Column(Integer, nullable=True, comment="做种时长限制（小时），NULL为不限制")
    seeding_ratio_limit = Column(Numeric(5, 2), nullable=True, comment="做种分享率限制，NULL为不限制")

    # HR相关（从PT资源继承）
    has_hr = Column(Boolean, default=False, nullable=False, comment="是否有HR要求")
    hr_days = Column(Integer, nullable=True, comment="需要保种天数")
    hr_seed_time = Column(Integer, nullable=True, comment="需要保种小时数")
    hr_ratio = Column(Numeric(5, 2), nullable=True, comment="需要分享率")

    # 时间信息
    added_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="添加时间")
    started_at = Column(TZDateTime(), nullable=True, comment="开始下载时间")
    completed_at = Column(TZDateTime(), nullable=True, comment="下载完成时间")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_at = Column(TZDateTime(), nullable=True, comment="错误发生时间")
    retry_count = Column(Integer, default=0, nullable=False, comment="重试次数")

    # 创建和更新时间
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 关系
    pt_resource = relationship("PTResource", back_populates="download_tasks")
    downloader_config = relationship("DownloaderConfig")
    user = relationship("User", back_populates="download_tasks")
    organize_config = relationship("OrganizeConfig", foreign_keys=[organize_config_id])
    storage_mount = relationship("StorageMount", foreign_keys=[storage_mount_id])
    # 注意：统一资源关联使用多态设计，无直接 relationship，需要应用层查询

    # 索引和约束
    __table_args__ = (
        Index("idx_download_tasks_task_hash", "task_hash"),
        Index("idx_download_tasks_pt_resource_id", "pt_resource_id"),
        Index("idx_download_tasks_downloader_config_id", "downloader_config_id"),
        Index("idx_download_tasks_organize_config_id", "organize_config_id"),
        Index("idx_download_tasks_storage_mount_id", "storage_mount_id"),
        Index("idx_download_tasks_media_type", "media_type"),
        Index("idx_download_tasks_unified_resource", "unified_table_name", "unified_resource_id"),
        Index("idx_download_tasks_status", "status"),
        Index("idx_download_tasks_status_completed_at", "status", "completed_at"),
        CheckConstraint(
            "status IN ('pending', 'downloading', 'paused', 'completed', 'seeding', 'error', 'deleted')",
            name="check_task_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="check_progress_range"),
        CheckConstraint(
            "media_type IN ('movie', 'tv', 'music', 'book', 'anime', 'adult', 'game', 'other')",
            name="check_media_type",
        ),
    )

    def __repr__(self):
        return f"<DownloadTask(hash={self.task_hash}, name={self.torrent_name}, status={self.status}, progress={self.progress}%)>"
