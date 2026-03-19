# -*- coding: utf-8 -*-
"""
媒体服务器相关 Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.base import BaseResponseSchema


# ============================================================================
# 媒体服务器配置 Schemas
# ============================================================================


class MediaServerConfigCreate(BaseModel):
    """创建媒体服务器配置请求"""

    type: str = Field(..., description="服务器类型：jellyfin/emby/plex")
    name: str = Field(..., description="配置名称")
    host: str = Field(..., description="服务器地址")
    port: int = Field(..., description="端口号")
    use_ssl: bool = Field(default=False, description="是否使用SSL")

    # 认证信息（根据服务器类型选择使用）
    api_key: Optional[str] = Field(None, description="API Key（Jellyfin/Emby）")
    token: Optional[str] = Field(None, description="访问令牌（Plex）")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")

    # 服务器特定配置
    server_config: Optional[Dict[str, Any]] = Field(
        None, description="服务器特定配置（JSON格式）"
    )

    # 功能开关
    is_default: bool = Field(default=False, description="是否默认服务器")
    auto_refresh_library: bool = Field(default=True, description="文件整理后自动刷新媒体库")
    sync_watch_history: bool = Field(default=True, description="同步观看历史")
    watch_history_sync_interval: int = Field(default=60, description="观看历史同步间隔（分钟）")

    # 路径映射
    library_path_mappings: Optional[List[Dict[str, str]]] = Field(
        None, description="路径映射配置"
    )


class MediaServerConfigUpdate(BaseModel):
    """更新媒体服务器配置请求"""

    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    use_ssl: Optional[bool] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    server_config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    auto_refresh_library: Optional[bool] = None
    sync_watch_history: Optional[bool] = None
    watch_history_sync_interval: Optional[int] = None
    library_path_mappings: Optional[List[Dict[str, str]]] = None


class MediaServerConfigResponse(BaseResponseSchema):
    """媒体服务器配置响应"""

    id: int
    user_id: int
    type: str
    name: str
    host: str
    port: int
    use_ssl: bool
    is_default: bool
    auto_refresh_library: bool
    sync_watch_history: bool
    watch_history_sync_interval: int
    status: str
    last_check_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    server_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    # 认证信息已设置标志（用于前端编辑时判断）
    has_api_key: Optional[bool] = None
    has_token: Optional[bool] = None
    has_password: Optional[bool] = None

    # 注意：不返回敏感字段（api_key, token, password）


# ============================================================================
# 观看历史 Schemas
# ============================================================================


class MediaServerWatchHistoryResponse(BaseResponseSchema):
    """观看历史响应"""

    id: int
    user_id: int
    media_server_config_id: int
    server_type: str
    server_item_id: str
    media_type: str
    title: str
    year: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    episode_title: Optional[str] = None
    play_count: int
    last_played_at: datetime
    play_duration_seconds: Optional[int] = None
    runtime_seconds: Optional[int] = None
    is_completed: bool
    
    # 额外扩展字段
    server_name: Optional[str] = None
    image_url: Optional[str] = None
    playback_url: Optional[str] = None
    playback_progress: float = 0
    
    # 本地关联
    unified_id: Optional[int] = Field(None, alias="unified_resource_id")
    
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class MediaServerWatchHistoryListResponse(BaseModel):
    """观看历史列表响应"""

    items: List[MediaServerWatchHistoryResponse]
    total: int
    page: int = 1
    page_size: int = 100


class MediaServerWatchStatisticsResponse(BaseModel):
    """观看统计响应"""

    total_count: int
    completed_count: int
    by_type: Dict[str, int]


# ============================================================================
# 媒体库 Schemas
# ============================================================================


class MediaServerLibraryResponse(BaseModel):
    """媒体库响应"""

    id: str
    name: str
    type: str
    locations: List[str]
    config_id: Optional[int] = None
    image_url: Optional[str] = None
    web_url: Optional[str] = None
    item_count: Optional[int] = 0
    last_scan_at: Optional[datetime] = None


class MediaServerStatsResponse(BaseModel):
    """媒体服务器统计响应"""

    stats_data: Dict[str, Any] = Field(..., description="统计数据（原始格式）")
    movie_count: int = Field(0, description="电影数量")
    tv_count: int = Field(0, description="剧集数量")
    episode_count: int = Field(0, description="总集数数据")
    user_count: int = Field(0, description="用户数量")


# ============================================================================
# 操作结果 Schemas
# ============================================================================


class MediaServerTestConnectionResponse(BaseModel):
    """连接测试响应"""

    success: bool
    message: str


class MediaServerRefreshLibraryResponse(BaseModel):
    """刷新媒体库响应"""

    success: bool
    message: Optional[str] = None


class MediaServerSyncHistoryResponse(BaseModel):
    """同步观看历史响应"""

    synced_count: int
    new_count: int
    updated_count: int


# ============================================================================
# 媒体服务器媒体项 Schemas
# ============================================================================


class MediaServerItemResponse(BaseResponseSchema):
    """媒体服务器媒体项响应"""

    id: int
    media_server_config_id: int
    server_type: str
    server_item_id: str
    library_id: Optional[str] = None
    library_name: Optional[str] = None

    # 媒体项基础信息
    item_type: str
    media_type: str
    name: str
    sort_name: Optional[str] = None
    original_name: Optional[str] = None
    year: Optional[int] = None
    premiere_date: Optional[datetime] = None
    date_created: Optional[datetime] = None

    # 电视剧特定字段
    series_id: Optional[str] = None
    series_name: Optional[str] = None
    season_id: Optional[str] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None

    # 文件信息
    file_path: Optional[str] = None
    file_size: Optional[int] = None

    # 本地资源关联
    media_file_id: Optional[int] = None
    unified_table_name: Optional[str] = None
    unified_resource_id: Optional[int] = None

    # 外部元数据ID
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    tvdb_id: Optional[int] = None

    # 播放统计
    play_count: int
    last_played_at: Optional[datetime] = None
    is_favorite: bool

    # 技术信息
    runtime_seconds: Optional[int] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None

    # 元数据
    overview: Optional[str] = None
    community_rating: Optional[str] = None
    critic_rating: Optional[str] = None
    official_rating: Optional[str] = None
    images: Optional[Dict[str, Any]] = None
    people: Optional[List[Dict[str, Any]]] = None
    genres: Optional[List[str]] = None
    studios: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    # 状态
    is_active: bool
    synced_at: datetime
    created_at: datetime
    updated_at: datetime

    # 额外字段（前端展示用）
    server_name: Optional[str] = None
    web_url: Optional[str] = None
    image_url: Optional[str] = None


class MediaServerItemListResponse(BaseModel):
    """媒体服务器媒体项列表响应"""

    items: List[MediaServerItemResponse]
    total: int
    page: int = 1
    page_size: int = 100


class MediaServerItemSyncResponse(BaseModel):
    """媒体服务器媒体项同步响应"""

    synced_count: int
    new_count: int
    updated_count: int
    deactivated_count: int
    matched_file_count: int
    matched_unified_count: int
