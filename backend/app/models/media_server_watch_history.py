# -*- coding: utf-8 -*-
"""
观看历史模型（从媒体服务器同步）
"""
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.json_types import JSON, TZDateTime


class MediaServerWatchHistory(Base):
    """观看历史表（从媒体服务器同步）"""

    __tablename__ = "media_server_watch_histories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 用户和配置关联
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    media_server_config_id = Column(
        Integer, ForeignKey("media_server_configs.id", ondelete="CASCADE"), nullable=False, comment="媒体服务器配置ID"
    )

    # 媒体服务器类型
    server_type = Column(String(50), nullable=False, comment="服务器类型：jellyfin/emby/plex")

    # 服务器端标识
    server_item_id = Column(String(100), nullable=False, comment="媒体服务器的媒体项ID")
    server_user_id = Column(String(100), nullable=False, comment="媒体服务器的用户ID")
    library_id = Column(String(100), nullable=True, index=True, comment="媒体库ID")

    # 媒体信息
    media_type = Column(String(20), nullable=False, index=True, comment="媒体类型：movie/tv/music")
    title = Column(String(500), nullable=False, comment="标题")
    year = Column(Integer, nullable=True, comment="年份")

    # 电视剧特定信息
    season_number = Column(Integer, nullable=True, comment="季数")
    episode_number = Column(Integer, nullable=True, comment="集数")
    episode_title = Column(String(500), nullable=True, comment="集标题")

    # 播放信息
    play_count = Column(Integer, default=1, nullable=False, comment="播放次数")
    last_played_at = Column(TZDateTime(), nullable=False, comment="最后播放时间")
    play_duration_seconds = Column(Integer, nullable=True, comment="播放时长（秒）")
    runtime_seconds = Column(Integer, nullable=True, comment="总时长（秒）")
    is_completed = Column(Boolean, default=False, nullable=False, comment="是否看完（>90%）")

    # 本地文件关联（支持 AI 推荐）
    media_file_id = Column(
        Integer, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True, index=True, comment="本地媒体文件ID"
    )
    unified_table_name = Column(String(50), nullable=True, comment="统一资源表名（如：unified_movies）")
    unified_resource_id = Column(Integer, nullable=True, comment="统一资源ID")

    # 原始数据（JSON格式，保留服务器原始响应）
    server_data = Column(
        JSON,
        nullable=True,
        comment="""媒体服务器原始响应数据，JSON格式：
        {
          "Name": "电影名称",
          "UserData": {
            "PlaybackPositionTicks": 0,
            "PlayCount": 1,
            "IsFavorite": false
          },
          ...
        }
        """,
    )

    # 时间戳
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 索引和约束
    __table_args__ = (
        Index("idx_media_server_watch_histories_server_item", "server_item_id", "user_id", "media_server_config_id"),
        Index("idx_media_server_watch_histories_unified", "unified_table_name", "unified_resource_id"),
        Index("idx_media_server_watch_histories_server_type", "server_type"),
        Index("idx_media_server_watch_histories_media_type", "media_type"),
        Index("idx_media_server_watch_histories_last_played", "last_played_at"),
    )

    def __repr__(self):
        return f"<MediaServerWatchHistory(title={self.title}, media_type={self.media_type}, server_type={self.server_type})>"
