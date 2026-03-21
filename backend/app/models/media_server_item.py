# -*- coding: utf-8 -*-
"""
媒体服务器媒体项模型（Jellyfin/Emby/Plex 通用）
存储媒体服务器中的所有媒体项，用于：
1. 缓存媒体库数据，提升查询性能
2. 关联本地媒体文件（media_files）
3. 关联统一资源（unified_*）
4. 支持播放历史统计
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

from app.core.json_types import JSON, TZDateTime
from app.constants.media import MEDIA_TYPES
from app.constants.media_server import MEDIA_SERVER_TYPES
from app.constants import UNIFIED_TABLES
from app.models.base import Base


class MediaServerItem(Base):
    """媒体服务器媒体项表（Jellyfin/Emby/Plex 通用）"""

    __tablename__ = "media_server_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ==================== 媒体服务器关联 ====================
    media_server_config_id = Column(
        Integer,
        ForeignKey("media_server_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="媒体服务器配置ID",
    )
    server_type = Column(String(50), nullable=False, index=True, comment="服务器类型：jellyfin/emby/plex")

    # ==================== 服务器端标识 ====================
    server_item_id = Column(String(100), nullable=False, index=True, comment="媒体服务器的媒体项ID（唯一）")
    library_id = Column(String(100), nullable=True, index=True, comment="媒体库ID")
    library_name = Column(String(200), nullable=True, comment="媒体库名称")

    # ==================== 媒体项类型和基础信息 ====================
    item_type = Column(
        String(50), nullable=False, index=True, comment="媒体项类型：Movie/Episode/Season/Series/Album/Audio/Photo"
    )
    media_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="媒体类型：movie/tv/music/book/anime/adult/game/other",
    )
    name = Column(String(500), nullable=False, comment="标题")
    sort_name = Column(String(500), nullable=True, comment="排序标题")
    original_name = Column(String(500), nullable=True, comment="原始标题")

    # ==================== 年份和日期 ====================
    year = Column(Integer, nullable=True, index=True, comment="年份")
    premiere_date = Column(TZDateTime(), nullable=True, comment="首映日期")
    date_created = Column(TZDateTime(), nullable=True, index=True, comment="加入媒体库时间（对应 Jellyfin DateCreated）")

    # ==================== 电视剧特定字段 ====================
    series_id = Column(String(100), nullable=True, index=True, comment="剧集ID（仅 Episode 类型）")
    series_name = Column(String(500), nullable=True, comment="剧集名称（仅 Episode 类型）")
    season_id = Column(String(100), nullable=True, index=True, comment="季ID（仅 Episode 类型）")
    season_number = Column(Integer, nullable=True, comment="季数")
    episode_number = Column(Integer, nullable=True, comment="集数")

    # ==================== 文件路径（关键关联字段） ====================
    file_path = Column(Text, nullable=True, index=True, comment="媒体服务器中的文件路径（用于匹配 media_files）")
    file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")

    # ==================== 本地资源关联 ====================
    media_file_id = Column(
        Integer,
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联的本地媒体文件ID",
    )
    unified_table_name = Column(String(50), nullable=True, index=True, comment="统一资源表名（如 unified_movies）")
    unified_resource_id = Column(Integer, nullable=True, index=True, comment="统一资源ID")

    # ==================== 外部元数据ID ====================
    tmdb_id = Column(Integer, nullable=True, index=True, comment="TMDB ID")
    imdb_id = Column(String(20), nullable=True, index=True, comment="IMDB ID")
    tvdb_id = Column(Integer, nullable=True, comment="TVDB ID")

    # ==================== 播放统计 ====================
    play_count = Column(Integer, default=0, nullable=False, comment="播放次数")
    last_played_at = Column(TZDateTime(), nullable=True, comment="最后播放时间")
    is_favorite = Column(Boolean, default=False, nullable=False, comment="是否收藏")

    # ==================== 技术信息 ====================
    runtime_ticks = Column(BigInteger, nullable=True, comment="总时长（Ticks，1秒 = 10000000 Ticks）")
    runtime_seconds = Column(Integer, nullable=True, comment="总时长（秒）")
    resolution = Column(String(20), nullable=True, comment="分辨率：2160p/1080p等")
    video_codec = Column(String(50), nullable=True, comment="视频编码")
    audio_codec = Column(String(50), nullable=True, comment="音频编码")

    # ==================== 元数据 ====================
    overview = Column(Text, nullable=True, comment="简介")
    community_rating = Column(String(10), nullable=True, comment="评分")
    critic_rating = Column(String(10), nullable=True, comment="影评人评分")
    official_rating = Column(String(50), nullable=True, comment="分级（如 PG-13, R）")

    # 图片路径（JSON格式）
    images = Column(
        JSON,
        nullable=True,
        comment="""图片路径，JSON格式：
        {
          "Primary": "/path/to/poster.jpg",
          "Backdrop": "/path/to/backdrop.jpg",
          "Logo": "/path/to/logo.png"
        }
        """,
    )

    # 人员信息（JSON格式）
    people = Column(
        JSON,
        nullable=True,
        comment="""演职人员，JSON格式：
        [
          {"Name": "Tom Hanks", "Role": "Actor", "Type": "Actor"},
          {"Name": "Steven Spielberg", "Role": "Director", "Type": "Director"}
        ]
        """,
    )

    # 流派（JSON数组）
    genres = Column(JSON, nullable=True, comment="流派列表，JSON数组：['Action', 'Drama']")

    # 工作室（JSON数组）
    studios = Column(JSON, nullable=True, comment="工作室列表，JSON数组：['Warner Bros.']")

    # 标签（JSON数组）
    tags = Column(JSON, nullable=True, comment="标签列表，JSON数组：['HDR', 'DolbyVision']")

    # ==================== 原始数据 ====================
    server_data = Column(
        JSON,
        nullable=True,
        comment="""媒体服务器原始响应数据（完整保留），JSON格式：
        {
          "Id": "123456",
          "Name": "电影名称",
          "Type": "Movie",
          "UserData": {
            "PlayCount": 1,
            "IsFavorite": false
          },
          ...（完整的服务器响应）
        }
        """,
    )

    # ==================== 同步状态 ====================
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="是否存在于媒体服务器（软删除标记）")
    synced_at = Column(TZDateTime(), nullable=False, comment="最后同步时间")

    # ==================== 时间戳 ====================
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # ==================== 关系 ====================
    media_server_config = relationship("MediaServerConfig", backref="media_items")
    media_file = relationship("MediaFile", backref="media_server_items", foreign_keys=[media_file_id])

    # ==================== 约束 ====================
    __table_args__ = (
        # 服务器类型约束
        CheckConstraint(
            f"server_type IN {tuple(MEDIA_SERVER_TYPES)}",
            name="ck_media_server_item_server_type",
        ),
        # 媒体类型约束
        CheckConstraint(
            f"media_type IN {tuple(MEDIA_TYPES)}",
            name="ck_media_server_item_media_type",
        ),
        # 统一资源表名约束
        CheckConstraint(
            f"unified_table_name IS NULL OR unified_table_name IN {tuple(UNIFIED_TABLES)}",
            name="ck_media_server_item_unified_table",
        ),
        # 复合唯一索引（每个服务器配置 + server_item_id 唯一）
        Index("uix_media_server_item_config_server_id", "media_server_config_id", "server_item_id", unique=True),
        # 关联查询索引
        Index("ix_media_server_item_unified", "unified_table_name", "unified_resource_id"),
        Index("ix_media_server_item_file_path", "file_path"),
        Index("ix_media_server_item_media_file", "media_file_id"),
        Index("ix_media_server_item_media_type_year", "media_type", "year"),
        Index("ix_media_server_item_series_season_episode", "series_id", "season_number", "episode_number"),
        Index("ix_media_server_item_tmdb", "tmdb_id"),
        Index("ix_media_server_item_imdb", "imdb_id"),
        Index("ix_media_server_item_active_synced", "is_active", "synced_at"),
        {"comment": "媒体服务器媒体项表 - 存储 Jellyfin/Emby/Plex 中的所有媒体项"},
    )

    def __repr__(self):
        return f"<MediaServerItem(id={self.id}, name='{self.name}', type='{self.item_type}', server_type='{self.server_type}')>"
