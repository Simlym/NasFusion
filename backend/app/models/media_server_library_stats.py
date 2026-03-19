# -*- coding: utf-8 -*-
"""
媒体服务器媒体库统计缓存模型
"""
from sqlalchemy import Column, DateTime, Integer, ForeignKey, Index
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.json_types import JSON


class MediaServerLibraryStats(Base):
    """媒体服务器媒体库统计缓存（通用）"""

    __tablename__ = "media_server_library_stats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 媒体服务器配置关联
    media_server_config_id = Column(
        Integer,
        ForeignKey("media_server_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="媒体服务器配置ID",
    )

    # 统计数据（JSON格式，不同服务器格式可能不同）
    stats_data = Column(
        JSON,
        nullable=False,
        comment="""媒体库统计数据，JSON格式（不同服务器可能有不同字段）：
        {
          "MovieCount": 150,
          "SeriesCount": 50,
          "EpisodeCount": 500,
          "AlbumCount": 100,
          "SongCount": 1000,
          "libraries": [
            {
              "id": "library_id_1",
              "name": "Movies",
              "type": "movies",
              "item_count": 150
            },
            {
              "id": "library_id_2",
              "name": "TV Shows",
              "type": "tvshows",
              "item_count": 50
            }
          ]
        }
        """,
    )

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 索引
    __table_args__ = (Index("idx_media_server_library_stats_config_id", "media_server_config_id"),)

    def __repr__(self):
        return f"<MediaServerLibraryStats(config_id={self.media_server_config_id})>"
