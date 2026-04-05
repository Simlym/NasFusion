# -*- coding: utf-8 -*-
"""
媒体文件Schema
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MediaFileBase(BaseModel):
    """媒体文件基础Schema"""

    file_path: str
    file_name: str
    directory: str
    file_size: int
    file_type: str
    extension: str
    media_type: str = "unknown"


class MediaFileCreate(MediaFileBase):
    """创建媒体文件Schema"""

    download_task_id: Optional[int] = None


class MediaFileUpdate(BaseModel):
    """更新媒体文件Schema"""

    status: Optional[str] = None
    media_type: Optional[str] = None
    unified_table_name: Optional[str] = None
    unified_resource_id: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    episode_title: Optional[str] = None
    match_method: Optional[str] = None
    match_confidence: Optional[int] = None


class MediaFileUpdateEpisodeInfo(BaseModel):
    """更新媒体文件集数信息"""

    season_number: Optional[int] = Field(None, description="季数")
    episode_number: Optional[int] = Field(None, description="集数")
    episode_title: Optional[str] = Field(None, description="集标题")


class MediaFileParseFilenameResponse(BaseModel):
    """从文件名解析季集信息的响应"""

    season: Optional[int] = None
    episode: Optional[int] = None
    title: Optional[str] = None
    episode_title: Optional[str] = None
    year: Optional[int] = None
    resolution: Optional[str] = None


class MediaFileResponse(MediaFileBase):
    """媒体文件响应Schema"""

    id: int
    file_hash: Optional[str] = None
    modified_at: datetime
    sub_title: Optional[str] = None

    # 媒体关联
    unified_table_name: Optional[str] = None
    unified_resource_id: Optional[int] = None
    download_task_id: Optional[int] = None

    # 从下载任务继承的配置（用于整理时的默认值）
    download_organize_config_id: Optional[int] = Field(default=None, description="下载任务关联的整理配置ID")
    download_storage_mount_id: Optional[int] = Field(default=None, description="下载任务关联的存储挂载点ID")

    # 识别和匹配
    match_method: str
    match_confidence: Optional[int] = None
    match_attempts: int

    # 电视剧特定
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    episode_title: Optional[str] = None

    # 处理状态
    status: str
    organized: bool
    organized_path: Optional[str] = None
    organized_at: Optional[datetime] = None
    organize_mode: Optional[str] = None

    # 技术信息
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    duration: Optional[int] = None
    tech_info: Optional[dict] = None

    # 元数据文件（实时检测，不存储在DB中）
    has_nfo: bool = False
    has_poster: bool = False

    # 外挂字幕 (保留，因为字幕属于文件属性，不同于海报等元数据)
    has_subtitle: bool = False
    subtitle_paths: Optional[List[str]] = None

    # 外部集成 (来自关联表 media_server_items)
    jellyfin_web_url: Optional[str] = Field(default=None, description="Jellyfin播放链接（如果文件已关联到媒体服务器）")

    # 错误追踪
    error_message: Optional[str] = None
    error_at: Optional[datetime] = None

    # 时间信息
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaFileListResponse(BaseModel):
    """媒体文件列表响应Schema"""

    total: int
    items: List[MediaFileResponse]


class MediaFileScanRequest(BaseModel):
    """扫描目录请求Schema"""

    directory: Optional[str] = None
    mount_type: Optional[str] = Field(default=None, description="按挂载点类型扫描 (如: download)")
    recursive: bool = True
    media_type: Optional[str] = None
    scan_mode: Optional[str] = "full"  # full或incremental


class MediaFileOrganizeRequest(BaseModel):
    """整理文件请求Schema"""

    file_ids: List[int]
    config_id: Optional[int] = None
    dry_run: bool = False
    force: bool = Field(default=False, description="强制重新整理（忽略已整理状态）")
    storage_mount_id: Optional[int] = Field(default=None, description="目标存储挂载点ID（可选，不传则自动选择）")


class MediaFileOrganizeResponse(BaseModel):
    """整理文件响应Schema"""

    status: str
    message: str
    organized_path: Optional[str] = None
    organize_mode: Optional[str] = None


# ========== 识别相关Schema ==========


class TMDBCandidate(BaseModel):
    """TMDB候选项Schema"""

    tmdb_id: int
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    rating_tmdb: Optional[float] = None
    votes_tmdb: Optional[int] = None
    genres: Optional[List[str]] = None
    media_type: str = "movie"  # movie 或 tv


class MediaFileIdentifyRequest(BaseModel):
    """识别请求Schema"""

    force_search: bool = Field(default=False, description="强制重新搜索（忽略已有关联）")


class MediaFileIdentifyResponse(BaseModel):
    """识别响应Schema"""

    success: bool
    candidates: List[TMDBCandidate] = []
    auto_matched: bool = False
    matched_id: Optional[int] = None
    match_source: Optional[str] = None
    parsed_info: Optional[dict] = None
    error: Optional[str] = None


class MediaFileLinkRequest(BaseModel):
    """关联到统一资源请求Schema"""

    tmdb_id: int
    media_type: str = Field(description="媒体类型: movie 或 tv")


class MediaFileLinkResponse(BaseModel):
    """关联到统一资源响应Schema"""

    success: bool
    unified_resource_id: Optional[int] = None
    message: str


class TMDBSearchRequest(BaseModel):
    """手动搜索TMDB请求Schema"""

    title: str
    year: Optional[int] = None
    media_type: str = Field(default="movie", description="媒体类型: movie 或 tv")


class TMDBSearchResponse(BaseModel):
    """手动搜索TMDB响应Schema"""

    results: List[TMDBCandidate] = []
    total: int = 0


# ========== 刮削相关Schema ==========


class MediaFileScrapeRequest(BaseModel):
    """刮削请求Schema"""

    config_id: Optional[int] = Field(
        default=None, description="整理配置ID，不指定则使用默认配置"
    )
    force: bool = Field(
        default=False, description="强制覆盖已存在的图片和NFO文件"
    )


class MediaFileScrapeResponse(BaseModel):
    """刮削响应Schema"""

    success: bool
    nfo_generated: bool = False
    poster_downloaded: bool = False
    backdrop_downloaded: bool = False
    nfo_path: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    errors: List[str] = []


class MediaFileBatchScrapeRequest(BaseModel):
    """批量刮削请求Schema"""

    file_ids: List[int]
    config_id: Optional[int] = Field(
        default=None, description="整理配置ID，不指定则使用默认配置"
    )


class MediaFileBatchScrapeResponse(BaseModel):
    """批量刮削响应Schema"""

    total: int
    success_count: int
    failed_count: int
    details: List[dict]


class MediaFileGenerateNFORequest(BaseModel):
    """生成NFO请求Schema"""

    config_id: Optional[int] = Field(
        default=None, description="整理配置ID，不指定则使用默认配置"
    )
    force: bool = Field(
        default=False, description="强制覆盖已存在的NFO文件"
    )


class MediaFileGenerateNFOResponse(BaseModel):
    """生成NFO响应Schema"""

    success: bool
    nfo_path: Optional[str] = None
    error: Optional[str] = None
