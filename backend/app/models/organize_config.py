# -*- coding: utf-8 -*-
"""
媒体文件整理配置模型
存储用户自定义的文件整理规则和目录结构模板
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.db_types import JSON, TZDateTime

from app.constants import (
    MEDIA_TYPES,
    NFO_FORMATS,
    ORGANIZE_MODES,
)
from app.models.base import Base


class OrganizeConfig(Base):
    """媒体文件整理配置表"""

    __tablename__ = "organize_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ==================== 基础配置 ====================
    name = Column(String(200), unique=True, nullable=False, comment="配置名称（唯一，如'电影库-4K'、'电视剧库'）")
    media_type = Column(String(20), nullable=False, index=True, comment="媒体类型：movie/tv/music/book/anime/adult")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否为默认配置")
    description = Column(Text, nullable=True, comment="配置描述")

    # ==================== 媒体库路径 ====================
    library_root = Column(Text, nullable=False, comment="媒体库根目录（绝对路径，如 /media/Movies）")

    # ==================== 目录结构模板 ====================
    # 支持的占位符：
    # 电影: {title}, {original_title}, {year}, {resolution}, {quality}
    # 电视剧: {title}, {year}, {season}, {season:02d}, {episode}, {episode:02d}, {episode_title}
    dir_template = Column(
        Text,
        nullable=False,
        comment="目录结构模板（如 '{title} ({year})'）",
    )
    filename_template = Column(
        Text,
        nullable=False,
        comment="文件名模板（如 '{title} ({year})'，不含扩展名）",
    )

    # ==================== 整理模式 ====================
    organize_mode = Column(
        String(20),
        default="hardlink",
        nullable=False,
        comment="整理模式：hardlink/symlink/move/copy",
    )

    # ==================== NFO和元数据配置 ====================
    generate_nfo = Column(Boolean, default=True, nullable=False, comment="是否生成NFO文件")
    nfo_format = Column(
        String(20),
        default="jellyfin",
        nullable=False,
        comment="NFO格式：jellyfin/emby/plex/kodi",
    )
    download_poster = Column(Boolean, default=True, nullable=False, comment="是否下载海报")
    download_backdrop = Column(Boolean, default=True, nullable=False, comment="是否下载背景图")
    poster_filename = Column(
        String(100),
        default="poster",
        nullable=False,
        comment="海报文件名（不含扩展名，默认 'poster'）",
    )
    backdrop_filename = Column(
        String(100),
        default="backdrop",
        nullable=False,
        comment="背景图文件名（不含扩展名，默认 'backdrop'）",
    )

    # ==================== 字幕配置 ====================
    organize_subtitles = Column(Boolean, default=True, nullable=False, comment="是否整理字幕文件")
    subtitle_filename_template = Column(
        Text,
        nullable=True,
        comment="字幕文件名模板（如 '{title} ({year}).{language}'）",
    )

    # ==================== 文件过滤 ====================
    min_file_size_mb = Column(Integer, nullable=True, comment="最小文件大小（MB），小于此大小的文件不处理")
    max_file_size_mb = Column(Integer, nullable=True, comment="最大文件大小（MB），大于此大小的文件不处理")
    include_extensions = Column(
        JSON,
        nullable=True,
        comment="包含的文件扩展名列表（JSON数组，如 ['.mkv', '.mp4']，NULL表示不限制）",
    )
    exclude_extensions = Column(
        JSON,
        nullable=True,
        comment="排除的文件扩展名列表（JSON数组，NULL表示不排除）",
    )
    exclude_keywords = Column(
        JSON,
        nullable=True,
        comment="排除的文件名关键词列表（JSON数组，如 ['sample', 'trailer']）",
    )

    # ==================== 高级选项 ====================
    skip_existed = Column(Boolean, default=True, nullable=False, comment="跳过已存在的文件")
    overwrite_nfo = Column(Boolean, default=False, nullable=False, comment="覆盖已存在的NFO文件")
    overwrite_poster = Column(Boolean, default=False, nullable=False, comment="覆盖已存在的海报")
    overwrite_backdrop = Column(Boolean, default=False, nullable=False, comment="覆盖已存在的背景图")

    # ==================== 字幕下载（预留）====================
    auto_download_subtitle = Column(Boolean, default=False, nullable=False, comment="是否自动下载字幕")
    subtitle_languages = Column(
        JSON,
        nullable=True,
        comment="字幕语言列表（JSON数组，如 ['chi', 'eng']）",
    )

    # ==================== 通知配置 ====================
    notify_on_success = Column(Boolean, default=False, nullable=False, comment="整理成功时发送通知")
    notify_on_failure = Column(Boolean, default=True, nullable=False, comment="整理失败时发送通知")

    # ==================== 统计信息 ====================
    total_organized_count = Column(Integer, default=0, nullable=False, comment="已整理文件数")
    last_organized_at = Column(TZDateTime(), nullable=True, comment="最后一次整理时间")

    # ==================== 时间信息 ====================
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # ==================== 约束 ====================
    __table_args__ = (
        # 媒体类型约束
        CheckConstraint(
            f"media_type IN {tuple(MEDIA_TYPES)}",
            name="ck_organize_config_media_type",
        ),
        # 整理模式约束
        CheckConstraint(
            f"organize_mode IN {tuple(ORGANIZE_MODES)}",
            name="ck_organize_config_organize_mode",
        ),
        # NFO格式约束
        CheckConstraint(
            f"nfo_format IN {tuple(NFO_FORMATS)}",
            name="ck_organize_config_nfo_format",
        ),
        # 文件大小约束
        CheckConstraint(
            "min_file_size_mb IS NULL OR min_file_size_mb > 0",
            name="ck_organize_config_min_size_positive",
        ),
        CheckConstraint(
            "max_file_size_mb IS NULL OR max_file_size_mb > 0",
            name="ck_organize_config_max_size_positive",
        ),
        CheckConstraint(
            "min_file_size_mb IS NULL OR max_file_size_mb IS NULL OR min_file_size_mb <= max_file_size_mb",
            name="ck_organize_config_size_range",
        ),
        {"comment": "媒体文件整理配置表 - 存储用户自定义的文件整理规则"},
    )

    def __repr__(self):
        return f"<OrganizeConfig(id={self.id}, name='{self.name}', media_type='{self.media_type}', enabled={self.is_enabled})>"
