# -*- coding: utf-8 -*-
"""
媒体文件模型
管理磁盘上的所有媒体文件及其处理状态
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
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db_types import JSON, TZDateTime

from app.constants import (
    FILE_TYPES,
    MATCH_METHODS,
    MEDIA_FILE_STATUSES,
    MEDIA_TYPES,
    UNIFIED_TABLES,
)
from app.models.base import Base


class MediaFile(Base):
    """媒体文件表"""

    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ==================== 文件基础信息 ====================
    file_path = Column(Text, unique=True, nullable=False, comment="完整文件路径（绝对路径，唯一）")
    file_name = Column(String(500), nullable=False, comment="文件名（包含扩展名）")
    directory = Column(Text, nullable=False, comment="所属目录（绝对路径）")
    file_size = Column(BigInteger, nullable=False, comment="文件大小（字节）")
    file_hash = Column(String(64), nullable=True, index=True, comment="文件SHA256哈希（用于去重，可选）")
    file_type = Column(
        String(20), nullable=False, index=True, comment="文件类型：video/audio/subtitle/other"
    )
    extension = Column(String(20), nullable=False, comment="文件扩展名（如 .mkv, .mp4）")
    modified_at = Column(TZDateTime(), nullable=False, comment="文件最后修改时间")

    # ==================== 媒体关联 ====================
    media_type = Column(
        String(20),
        nullable=False,
        default="unknown",
        index=True,
        comment="媒体类型：movie/tv/music/book/anime/adult/unknown",
    )
    unified_table_name = Column(
        String(50), nullable=True, index=True, comment="统一资源表名（如 unified_movies）"
    )
    unified_resource_id = Column(Integer, nullable=True, index=True, comment="统一资源ID")
    download_task_id = Column(
        Integer, ForeignKey("download_tasks.id"), nullable=True, index=True, comment="关联的下载任务ID"
    )
    media_directory_id = Column(
        Integer, ForeignKey("media_directories.id"), nullable=True, index=True, comment="所属媒体目录ID"
    )

    # ==================== 识别和匹配 ====================
    match_method = Column(
        String(30),
        nullable=False,
        default="none",
        comment="匹配方法：from_download/from_pt_title/from_filename/from_mediainfo/manual/none",
    )
    match_confidence = Column(Integer, nullable=True, comment="匹配置信度 0-100")
    match_attempts = Column(Integer, default=0, nullable=False, comment="尝试识别次数")
    match_detail = Column(JSON, nullable=True, comment="匹配详情（JSON对象，存储识别过程信息）")

    # ==================== 电视剧特定字段 ====================
    season_number = Column(Integer, nullable=True, comment="季数（仅电视剧）")
    episode_number = Column(Integer, nullable=True, comment="集数（仅电视剧）")
    episode_title = Column(String(500), nullable=True, comment="集标题（仅电视剧）")

    # ==================== PT资源信息（快照） ====================
    sub_title = Column(String(500), nullable=True, comment="副标题（从PT资源复制，避免relationship问题）")

    # ==================== 处理状态 ====================
    status = Column(
        String(20),
        default="discovered",
        nullable=False,
        index=True,
        comment="状态：discovered/identifying/identified/organizing/scraping/completed/failed/ignored",
    )
    sub_status = Column(JSON, nullable=True, comment="子状态详情（JSON对象，存储当前处理阶段的详细信息）")
    organized = Column(Boolean, default=False, nullable=False, index=True, comment="是否已整理")
    organized_path = Column(Text, nullable=True, comment="整理后的文件路径")
    organized_at = Column(TZDateTime(), nullable=True, comment="整理时间")
    organize_mode = Column(String(20), nullable=True, comment="整理模式：hardlink/reflink/symlink/move/copy")

    # ==================== 技术信息 ====================
    resolution = Column(String(20), nullable=True, comment="分辨率标签：2160p/1080p等")
    video_codec = Column(String(50), nullable=True, comment="视频编码：HEVC/AVC等")
    duration = Column(Integer, nullable=True, comment="时长（秒）")
    tech_info = Column(JSON, nullable=True, comment="完整技术元数据(mediainfo, tracks, bitrates)")

    # ==================== 外部集成 ====================
    # ==================== 外部集成 ====================
    # Jellyfin等外部同步信息移至专门的关联表，此处移除

    # ==================== 错误追踪 ====================
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_at = Column(TZDateTime(), nullable=True, comment="错误发生时间")
    error_step = Column(String(50), nullable=True, comment="错误发生阶段")

    # ==================== 时间信息 ====================
    discovered_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="发现时间")
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # ==================== 关系 ====================
    download_task = relationship("DownloadTask", backref="media_files")
    media_directory = relationship("MediaDirectory", back_populates="files", foreign_keys=[media_directory_id])

    # ==================== 约束 ====================
    __table_args__ = (
        # 文件类型约束
        CheckConstraint(
            f"file_type IN {tuple(FILE_TYPES)}",
            name="ck_media_file_file_type",
        ),
        # 媒体类型约束
        CheckConstraint(
            f"media_type IN {tuple(MEDIA_TYPES + ['unknown'])}",
            name="ck_media_file_media_type",
        ),
        # 状态约束
        CheckConstraint(
            f"status IN {tuple(MEDIA_FILE_STATUSES)}",
            name="ck_media_file_status",
        ),
        # 匹配方法约束
        CheckConstraint(
            f"match_method IN {tuple(MATCH_METHODS)}",
            name="ck_media_file_match_method",
        ),
        # 统一资源表名约束
        CheckConstraint(
            f"unified_table_name IS NULL OR unified_table_name IN {tuple(UNIFIED_TABLES)}",
            name="ck_media_file_unified_table",
        ),
        # 匹配置信度范围约束
        CheckConstraint(
            "match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 100)",
            name="ck_media_file_confidence_range",
        ),
        # 电视剧季数集数约束
        CheckConstraint(
            "season_number IS NULL OR season_number > 0",
            name="ck_media_file_season_positive",
        ),
        CheckConstraint(
            "episode_number IS NULL OR episode_number > 0",
            name="ck_media_file_episode_positive",
        ),
        # 复合索引
        Index("ix_media_file_media_resource", "unified_table_name", "unified_resource_id"),
        Index("ix_media_file_status_organized", "status", "organized"),
        Index("ix_media_file_media_type_status", "media_type", "status"),
        Index("ix_media_file_tv_episode", "unified_resource_id", "season_number", "episode_number"),
        Index("ix_media_file_discovered_at", "discovered_at"),
        {"comment": "媒体文件表 - 管理所有磁盘上的媒体文件及其处理状态"},
    )

    def __repr__(self):
        return f"<MediaFile(id={self.id}, file_name='{self.file_name}', media_type='{self.media_type}', status='{self.status}')>"
