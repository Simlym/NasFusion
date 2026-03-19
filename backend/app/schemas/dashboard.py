# -*- coding: utf-8 -*-
"""
仪表盘相关Schemas
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.media_server import MediaServerWatchHistoryResponse
from app.schemas.task_execution import TaskExecutionSummary


class MediaBackdropItem(BaseModel):
    """用于 Hero 轮播的媒体背景图项"""

    id: int
    media_type: str  # "movie" | "tv"
    title: str
    year: Optional[int] = None
    backdrop_url: str
    poster_url: Optional[str] = None
    rating: Optional[float] = None
    overview: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    """仪表盘统计信息响应（纯 DB count，快速返回）"""

    # 发现：PT 资源 / 电影 / 剧集 / 演员库
    total_sites: int = Field(..., description="PT站点总数")
    total_resources: int = Field(..., description="资源总数")
    total_movies: int = Field(..., description="电影总数")
    total_tvs: int = Field(..., description="剧集总数")
    total_actors: int = Field(0, description="演员库总数")

    # 媒体：订阅 / 下载 / 存储 / 媒体服务器
    total_subscriptions: int = Field(..., description="订阅总数")
    total_downloads: int = Field(0, description="下载任务总数（全量）")
    active_downloads: int = Field(..., description="活跃下载任务数（进行中）")
    total_storage_used: int = Field(..., description="存储使用总量(字节)")
    media_server_count: int = Field(0, description="媒体服务器数量")
    total_media_items: int = Field(0, description="媒体服务器管理的所有条目总数")

    # 系统：图片缓存
    image_cache_count: int = Field(..., description="图片缓存数量")
    image_cache_size: int = Field(..., description="图片缓存总大小(字节)")

    # 今日新增统计
    today_new_resources: int = Field(0, description="今日新增PT资源数")
    today_new_movies: int = Field(0, description="今日新增电影数")
    today_new_tvs: int = Field(0, description="今日新增剧集数")
    today_updated_tvs: int = Field(0, description="今日更新剧集数（非新增）")
    today_new_actors: int = Field(0, description="今日新增演员数")
    today_new_subscriptions: int = Field(0, description="今日新增订阅数")
    today_new_downloads: int = Field(0, description="今日新增下载任务数")

    # 媒体服务器数据
    recent_watch_history: List[MediaServerWatchHistoryResponse] = Field(
        default_factory=list, description="最近观看历史"
    )

    # Hero 轮播背景图
    recent_media_backdrops: List[MediaBackdropItem] = Field(
        default_factory=list, description="最近有背景图的媒体，用于 Hero 轮播展示"
    )

    # 最近活动（保留向后兼容，推荐改用 /dashboard/activity 懒加载）
    recent_activities: List[TaskExecutionSummary] = Field(
        default_factory=list, description="最近活动列表"
    )


class DashboardActivityResponse(BaseModel):
    """仪表盘近期活动（独立懒加载接口）"""

    recent_activities: List[TaskExecutionSummary] = Field(..., description="最近活动列表")


class DashboardBackdropsResponse(BaseModel):
    """仪表盘 Hero 轮播背景图（独立懒加载接口）"""

    recent_media_backdrops: List[MediaBackdropItem] = Field(
        default_factory=list, description="最近有背景图的媒体，用于 Hero 轮播展示"
    )


class DashboardWatchHistoryResponse(BaseModel):
    """仪表盘观看历史（独立懒加载接口）"""

    watch_history: List[MediaServerWatchHistoryResponse] = Field(
        default_factory=list, description="最近观看历史"
    )
