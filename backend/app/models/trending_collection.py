# -*- coding: utf-8 -*-
"""
榜单收藏模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, JSON

from app.models.base import BaseModel


class TrendingCollection(BaseModel):
    """榜单收藏表（单表设计，支持多态关联）"""

    __tablename__ = "trending_collections"

    # 榜单分类
    collection_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="榜单类型：douban_hot_movie/tmdb_popular_movie/douban_hot_tv等",
    )

    # 媒体类型
    media_type = Column(
        String(20), nullable=False, index=True, comment="媒体类型：movie/tv"
    )

    # 榜单位置
    rank_position = Column(Integer, nullable=False, comment="榜单位置（1-100）")

    # 来源信息（阶段一：快速落表时填充）
    source_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="来源类型：douban/tmdb",
    )
    source_id = Column(
        String(50),
        nullable=False,
        index=True,
        comment="来源ID（豆瓣ID或TMDB ID）",
    )
    raw_data = Column(
        JSON,
        nullable=True,
        comment="原始元数据快照（标题、海报、评分等基础信息）",
    )

    # 关联信息（阶段二：异步任务填充）
    unified_resource_id = Column(
        Integer,
        nullable=True,  # 改为可空，异步填充
        index=True,
        comment="统一资源ID（指向 unified_movies.id 或 unified_tv_series.id）",
    )
    detail_synced = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="详情是否已同步",
    )

    # 同步信息
    synced_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        # 联合唯一索引：同一榜单类型下，同一来源ID只能出现一次
        Index(
            "idx_collection_source_unique",
            "collection_type",
            "source_type",
            "source_id",
            unique=True,
        ),
        # 联合索引：加速榜单查询
        Index("idx_collection_rank", "collection_type", "rank_position"),
        # 索引：加速待同步查询
        Index("idx_collection_pending", "detail_synced"),
    )

    def __repr__(self):
        return (
            f"<TrendingCollection(id={self.id}, "
            f"collection_type={self.collection_type}, "
            f"rank={self.rank_position})>"
        )
