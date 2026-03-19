# -*- coding: utf-8 -*-
"""
订阅系统 Pydantic Schema
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.constants.subscription import (
    DEFAULT_CHECK_STRATEGY,
    DEFAULT_COMPLETE_CONDITION,
    DEFAULT_START_EPISODE,
    SUBSCRIPTION_PRIORITY_DEFAULT,
    SUBSCRIPTION_PRIORITY_MAX,
    SUBSCRIPTION_PRIORITY_MIN,
    SUBSCRIPTION_STATUS_ACTIVE,
)
from app.schemas.base import BaseResponseSchema


# ==================== 订阅规则Schema ====================
class SubscriptionRulesSchema(BaseModel):
    """订阅规则Schema"""

    quality_priority: Optional[List[str]] = Field(
        default=None,
        description="质量优先级列表 ['2160p', '1080p', '720p']",
    )
    quality_mode: Optional[str] = Field(
        default=None,
        description="质量匹配模式: first_match/best_match（已废弃，保留兼容）",
    )
    site_priority: Optional[List[int]] = Field(
        default=None,
        description="站点优先级列表（站点ID）",
    )
    promotion_required: Optional[List[str]] = Field(
        default=None,
        description="必须满足的促销类型 ['free', '2xfree', '2x', '50%', '30%']",
    )
    min_seeders: Optional[int] = Field(
        default=0,
        ge=0,
        description="最小做种数",
    )
    min_file_size: Optional[int] = Field(
        default=0,
        ge=0,
        description="最小文件大小（MB）",
    )
    episode_type_preference: Optional[str] = Field(
        default="both",
        description="集数类型偏好: single_preferred/season_preferred/both",
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


# ==================== 创建订阅 ====================
class SubscriptionCreateSchema(BaseModel):
    """创建订阅Schema"""

    # 基础信息（必填）
    media_type: str = Field(..., description="媒体类型: movie/tv")
    unified_movie_id: Optional[int] = Field(None, description="电影资源ID（media_type='movie'时必填）")
    unified_tv_id: Optional[int] = Field(None, description="电视剧资源ID（media_type='tv'时必填）")
    title: str = Field(..., min_length=1, max_length=500, description="订阅标题")

    # 可选基础信息
    original_title: Optional[str] = Field(None, max_length=500, description="原始标题")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="年份")
    poster_url: Optional[str] = Field(None, description="海报URL")

    # 外部ID
    douban_id: Optional[str] = Field(None, description="豆瓣ID")
    imdb_id: Optional[str] = Field(None, description="IMDB ID")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID")

    # 订阅来源和类型
    source: Optional[str] = Field(None, description="订阅来源: from_tmdb/from_pt_resource/manual")
    subscription_type: Optional[str] = Field(None, description="订阅类型: movie_release/tv_season")

    # 电视剧订阅字段
    current_season: Optional[int] = Field(None, ge=1, description="订阅的季度")
    start_episode: Optional[int] = Field(
        DEFAULT_START_EPISODE,
        ge=1,
        description="起始集数（从第几集开始）"
    )
    total_episodes: Optional[int] = Field(None, ge=1, description="本季总集数")

    # 多资源关联（解决长篇动画跨年番匹配问题）
    related_tv_ids: Optional[List[int]] = Field(
        None,
        description="关联的TV资源ID列表（同一系列的不同年番/季度）"
    )
    absolute_episode_start: Optional[int] = Field(
        None,
        ge=1,
        description="绝对集数起始（不区分季度），启用后使用绝对集数匹配模式"
    )
    absolute_episode_end: Optional[int] = Field(
        None,
        ge=1,
        description="绝对集数结束（留空表示持续追更）"
    )

    # 展示信息覆写（用于NFO生成和文件整理）
    override_title: Optional[str] = Field(
        None,
        max_length=500,
        description="覆写标题（用于NFO），例如: '仙逆' 而非 '仙逆 年番2'"
    )
    override_year: Optional[int] = Field(
        None,
        ge=1900,
        le=2100,
        description="覆写年份（用于NFO和文件整理）"
    )
    override_folder: Optional[str] = Field(
        None,
        max_length=500,
        description="覆写存储目录名，例如: '仙逆 (2023)'"
    )
    use_override_for_sync: bool = Field(
        False,
        description="是否使用覆写标题进行PT资源同步（解决如'仙逆 年番2'需要用'仙逆'搜索的问题）"
    )

    # 订阅规则
    rules: Optional[SubscriptionRulesSchema] = Field(None, description="订阅规则")

    # 检查策略（check_interval 由系统统一管理，不再支持单独配置）
    check_strategy: str = Field(DEFAULT_CHECK_STRATEGY, description="检查策略")

    # 完成条件
    complete_condition: str = Field(DEFAULT_COMPLETE_CONDITION, description="完成条件")
    auto_complete_on_download: bool = Field(False, description="下载后自动完成")

    # 通知设置
    notify_on_match: bool = Field(True, description="匹配时通知")
    notify_on_download: bool = Field(True, description="下载时通知")
    notification_channels: Optional[List[int]] = Field(None, description="通知渠道ID列表")

    # 下载设置
    auto_download: bool = Field(False, description="是否自动下载")

    # 整理设置
    auto_organize: bool = Field(True, description="下载完成后是否自动整理")
    organize_config_id: Optional[int] = Field(None, description="整理配置ID（空=使用全局默认）")
    storage_mount_id: Optional[int] = Field(None, description="存储挂载点ID（空=使用全局默认）")

    # 用户设置
    user_tags: Optional[List[str]] = Field(None, description="用户标签")
    user_priority: int = Field(
        SUBSCRIPTION_PRIORITY_DEFAULT,
        ge=SUBSCRIPTION_PRIORITY_MIN,
        le=SUBSCRIPTION_PRIORITY_MAX,
        description="用户优先级(1-10)"
    )
    user_notes: Optional[str] = Field(None, description="用户备注")
    is_favorite: bool = Field(False, description="是否收藏")

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, v):
        """验证媒体类型"""
        if v not in ["movie", "tv"]:
            raise ValueError("media_type must be 'movie' or 'tv'")
        return v

    def model_post_init(self, __context) -> None:
        """模型初始化后的验证"""
        # 电视剧订阅时，total_episodes 必填
        if self.media_type == "tv" and self.total_episodes is None:
            raise ValueError("电视剧订阅必须提供 total_episodes（总集数）")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


# ==================== 更新订阅 ====================
class SubscriptionUpdateSchema(BaseModel):
    """更新订阅Schema（所有字段可选）"""

    # 基础信息
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="订阅标题")
    original_title: Optional[str] = Field(None, max_length=500, description="原始标题")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="年份")
    poster_url: Optional[str] = Field(None, description="海报URL")

    # 电视剧订阅字段
    current_season: Optional[int] = Field(None, ge=1, description="订阅的季度")
    start_episode: Optional[int] = Field(None, ge=1, description="起始集数")
    current_episode: Optional[int] = Field(None, ge=1, description="当前集数")
    total_episodes: Optional[int] = Field(None, ge=1, description="本季总集数")

    # 多资源关联
    related_tv_ids: Optional[List[int]] = Field(None, description="关联的TV资源ID列表")
    absolute_episode_start: Optional[int] = Field(None, ge=1, description="绝对集数起始")
    absolute_episode_end: Optional[int] = Field(None, ge=1, description="绝对集数结束")

    # 展示信息覆写
    override_title: Optional[str] = Field(None, max_length=500, description="覆写标题")
    override_year: Optional[int] = Field(None, ge=1900, le=2100, description="覆写年份")
    override_folder: Optional[str] = Field(None, max_length=500, description="覆写存储目录名")
    use_override_for_sync: Optional[bool] = Field(None, description="是否使用覆写标题进行PT资源同步")

    # 订阅规则
    rules: Optional[SubscriptionRulesSchema] = Field(None, description="订阅规则")

    # 订阅状态
    status: Optional[str] = Field(None, description="订阅状态")
    is_active: Optional[bool] = Field(None, description="是否激活")

    # 检查策略（check_interval 由系统统一管理，不再支持单独配置）
    check_strategy: Optional[str] = Field(None, description="检查策略")

    # 完成条件
    complete_condition: Optional[str] = Field(None, description="完成条件")
    auto_complete_on_download: Optional[bool] = Field(None, description="下载后自动完成")

    # 通知设置
    notify_on_match: Optional[bool] = Field(None, description="匹配时通知")
    notify_on_download: Optional[bool] = Field(None, description="下载时通知")
    notification_channels: Optional[List[int]] = Field(None, description="通知渠道ID列表")

    # 下载设置
    auto_download: Optional[bool] = Field(None, description="是否自动下载")

    # 整理设置
    auto_organize: Optional[bool] = Field(None, description="下载完成后是否自动整理")
    organize_config_id: Optional[int] = Field(None, description="整理配置ID（空=使用全局默认）")
    storage_mount_id: Optional[int] = Field(None, description="存储挂载点ID（空=使用全局默认）")

    # 用户设置
    user_tags: Optional[List[str]] = Field(None, description="用户标签")
    user_priority: Optional[int] = Field(
        None,
        ge=SUBSCRIPTION_PRIORITY_MIN,
        le=SUBSCRIPTION_PRIORITY_MAX,
        description="用户优先级"
    )
    user_notes: Optional[str] = Field(None, description="用户备注")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


# ==================== 订阅响应 ====================
class SubscriptionResponse(BaseResponseSchema):
    """订阅响应Schema"""

    id: int
    user_id: int

    # 基础信息
    media_type: str
    unified_movie_id: Optional[int] = None
    unified_tv_id: Optional[int] = None
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None

    # 外部ID
    douban_id: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None

    # 订阅来源和类型
    source: Optional[str] = None
    subscription_type: Optional[str] = None

    # 电视剧订阅字段
    current_season: Optional[int] = None
    start_episode: Optional[int] = None
    current_episode: Optional[int] = None
    total_episodes: Optional[int] = None
    episodes_status: Optional[Dict[str, Any]] = None

    # 多资源关联
    related_tv_ids: Optional[List[int]] = None
    absolute_episode_start: Optional[int] = None
    absolute_episode_end: Optional[int] = None

    # 展示信息覆写
    override_title: Optional[str] = None
    override_year: Optional[int] = None
    override_folder: Optional[str] = None
    use_override_for_sync: bool = False

    # 订阅规则
    rules: Optional[Dict[str, Any]] = None

    # 订阅状态
    status: str
    is_active: bool

    # 检查策略
    check_strategy: str
    last_check_at: Optional[datetime] = None

    # 完成条件
    complete_condition: str
    auto_complete_on_download: bool

    # 资源状态
    has_resources: bool
    first_resource_found_at: Optional[datetime] = None

    # 通知设置
    notify_on_match: bool
    notify_on_download: bool
    notification_channels: Optional[List[int]] = None

    # 下载设置
    auto_download: bool

    # 整理设置
    auto_organize: bool
    organize_config_id: Optional[int] = None
    storage_mount_id: Optional[int] = None

    # 用户设置
    user_tags: Optional[List[str]] = None
    user_priority: int
    user_notes: Optional[str] = None
    is_favorite: bool

    # 统计信息
    total_checks: int
    total_matches: int
    total_downloads: int

    # 时间戳
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


# ==================== 订阅列表响应 ====================
class SubscriptionListResponse(BaseModel):
    """订阅列表响应Schema"""

    total: int = Field(..., description="总数")
    items: List[SubscriptionResponse] = Field(..., description="订阅列表")

    model_config = ConfigDict(from_attributes=True)


# ==================== 订阅检查日志响应 ====================
class SubscriptionCheckLogResponse(BaseResponseSchema):
    """订阅检查日志响应Schema"""

    id: int
    subscription_id: int
    check_at: datetime

    # PT搜索结果
    sites_searched: Optional[int] = None
    resources_found: Optional[int] = None
    match_count: Optional[int] = None
    best_match: Optional[Dict[str, Any]] = None
    search_results: Optional[Dict[str, Any]] = None

    # 匹配分析
    matching_analysis: Optional[Dict[str, Any]] = None

    # 触发的动作
    action_triggered: Optional[str] = None
    action_detail: Optional[Dict[str, Any]] = None

    # 执行状态
    execution_time: Optional[int] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    error_severity: str

    # 任务执行关联
    task_execution_id: Optional[int] = None

    # 时间戳
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


# ==================== 订阅检查日志列表响应 ====================
class SubscriptionCheckLogListResponse(BaseModel):
    """订阅检查日志列表响应Schema"""

    total: int = Field(..., description="总数")
    items: List[SubscriptionCheckLogResponse] = Field(..., description="检查日志列表")

    model_config = ConfigDict(from_attributes=True)


# ==================== 集数状态相关Schema ====================
class EpisodeStatusSchema(BaseModel):
    """单集状态Schema"""

    status: str = Field(..., description="状态: downloaded/downloading/available/waiting/failed/ignored")

    # downloaded 时的字段
    file_id: Optional[int] = Field(None, description="媒体文件ID")
    quality: Optional[str] = Field(None, description="质量")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    file_path: Optional[str] = Field(None, description="文件路径")
    downloaded_at: Optional[datetime] = Field(None, description="下载完成时间")

    # downloading 时的字段
    task_id: Optional[int] = Field(None, description="下载任务ID")
    progress: Optional[int] = Field(None, ge=0, le=100, description="下载进度")
    started_at: Optional[datetime] = Field(None, description="开始下载时间")

    # available 时的字段
    resource_ids: Optional[List[int]] = Field(None, description="可用PT资源ID列表")
    qualities: Optional[List[str]] = Field(None, description="可用质量列表")
    best_quality: Optional[str] = Field(None, description="最佳质量")
    resource_count: Optional[int] = Field(None, description="资源数量")
    found_at: Optional[datetime] = Field(None, description="发现时间")

    # waiting/failed 时的字段
    checked_at: Optional[datetime] = Field(None, description="检查时间")
    error: Optional[str] = Field(None, description="错误信息")
    failed_at: Optional[datetime] = Field(None, description="失败时间")

    # 通用字段
    note: Optional[str] = Field(None, description="备注信息")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )


class EpisodeStatusUpdateRequest(BaseModel):
    """手动更新集数状态请求"""

    status: str = Field(
        ...,
        description="目标状态: downloaded/ignored/waiting",
    )
    note: Optional[str] = Field(None, description="备注（如：手动标记）")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"downloaded", "ignored", "waiting"}
        if v not in allowed:
            raise ValueError(f"status 必须为 {allowed} 之一")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class EpisodesStatusStatsSchema(BaseModel):
    """集数状态统计Schema"""

    total: int = Field(..., description="总集数")
    downloaded: int = Field(..., description="已下载集数")
    downloading: int = Field(..., description="下载中集数")
    available: int = Field(..., description="有资源集数")
    waiting: int = Field(..., description="等待中集数")
    failed: int = Field(..., description="失败集数")
    ignored: int = Field(0, description="已忽略集数")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )


class EpisodesStatusResponse(BaseResponseSchema):
    """集数状态响应Schema"""

    subscription_id: int = Field(..., description="订阅ID")
    season: int = Field(..., description="季度")
    start_episode: int = Field(..., description="起始集数")
    total_episodes: int = Field(..., description="总集数")
    episodes: Dict[str, EpisodeStatusSchema] = Field(..., description="集数状态（key为集数字符串）")
    stats: EpisodesStatusStatsSchema = Field(..., description="统计信息")
    last_updated: datetime = Field(..., description="最后更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )
