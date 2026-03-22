# -*- coding: utf-8 -*-
"""
媒体目录模型
"""
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, JSON, Index, CheckConstraint

from app.core.db_types import TZDateTime
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.utils.timezone import now
from app.constants import MEDIA_TYPES


class MediaDirectory(Base):
    """媒体目录表 - 按目录存储媒体元数据"""
    __tablename__ = "media_directories"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 目录信息
    directory_path = Column(String(1024), unique=True, nullable=False, index=True, comment="目录完整路径")
    directory_name = Column(String(512), nullable=False, comment="目录名称")
    parent_id = Column(Integer, ForeignKey("media_directories.id"), nullable=True, index=True, comment="父目录ID (自关联)")

    # 媒体类型和关联
    media_type = Column(String(50), nullable=True, index=True, comment="媒体类型 (movie/tv_series/anime/music/book/adult/game/other)")
    unified_table_name = Column(String(100), nullable=True, comment="统一资源表名")
    unified_resource_id = Column(Integer, nullable=True, index=True, comment="统一资源ID")

    # TV剧集专用字段
    series_name = Column(String(512), nullable=True, comment="剧集名称")
    season_number = Column(Integer, nullable=True, comment="季度编号")
    episode_count = Column(Integer, default=0, comment="集数统计")

    # 元数据文件
    has_nfo = Column(Boolean, default=False, comment="是否存在NFO文件")
    nfo_path = Column(String(1024), nullable=True, comment="NFO文件路径")
    has_poster = Column(Boolean, default=False, comment="是否存在海报")
    poster_path = Column(String(1024), nullable=True, comment="海报路径")
    has_backdrop = Column(Boolean, default=False, comment="是否存在背景图")
    backdrop_path = Column(String(1024), nullable=True, comment="背景图路径")

    # 问题标记 (JSON格式)
    issue_flags = Column(
        JSON,
        default=dict,
        comment="问题标记: {missing_poster, missing_nfo, unidentified, duplicate, missing_files}"
    )

    # 统计信息
    total_files = Column(Integer, default=0, comment="文件总数")
    total_size = Column(BigInteger, default=0, comment="总大小 (字节)")

    # 时间戳
    scanned_at = Column(TZDateTime(), nullable=True, comment="最后扫描时间")
    source_mtime = Column(BigInteger, default=0, nullable=True, comment="源目录最后修改时间(mtime)")
    created_at = Column(TZDateTime(), default=now, nullable=False, comment="创建时间")
    updated_at = Column(TZDateTime(), default=now, onupdate=now, nullable=False, comment="更新时间")

    # 关系
    children = relationship(
        "MediaDirectory",
        backref="parent",
        foreign_keys=[parent_id],
        remote_side=[id]
    )
    files = relationship(
        "MediaFile",
        back_populates="media_directory",
        foreign_keys="MediaFile.media_directory_id"
    )

    # 约束
    __table_args__ = (
        CheckConstraint(
            f"media_type IS NULL OR media_type IN {tuple(MEDIA_TYPES)}",
            name="check_media_directory_media_type"
        ),
        Index("idx_media_dir_unified_resource", "unified_table_name", "unified_resource_id"),
        Index("idx_media_dir_series_season", "series_name", "season_number"),
        Index("idx_media_dir_type_path", "media_type", "directory_path"),
    )

    def __repr__(self):
        return f"<MediaDirectory(id={self.id}, path={self.directory_path}, type={self.media_type})>"
