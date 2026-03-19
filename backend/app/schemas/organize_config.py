# -*- coding: utf-8 -*-
"""
整理配置Schema
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrganizeConfigBase(BaseModel):
    """整理配置基础Schema"""

    name: str
    media_type: str
    library_root: str
    dir_template: str
    filename_template: str
    organize_mode: str = "hardlink"
    is_enabled: bool = True
    is_default: bool = False
    description: Optional[str] = None


class OrganizeConfigCreate(OrganizeConfigBase):
    """创建整理配置Schema"""

    # NFO和元数据配置
    generate_nfo: bool = True
    nfo_format: str = "jellyfin"
    download_poster: bool = True
    download_backdrop: bool = True
    poster_filename: str = "poster"
    backdrop_filename: str = "backdrop"

    # 字幕配置
    organize_subtitles: bool = True
    subtitle_filename_template: Optional[str] = None

    # 文件过滤
    min_file_size_mb: Optional[int] = None
    max_file_size_mb: Optional[int] = None
    include_extensions: Optional[List[str]] = None
    exclude_extensions: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None

    # 高级选项
    skip_existed: bool = True
    overwrite_nfo: bool = False
    overwrite_poster: bool = False
    overwrite_backdrop: bool = False

    # 字幕下载
    auto_download_subtitle: bool = False
    subtitle_languages: Optional[List[str]] = None

    # 通知配置
    notify_on_success: bool = False
    notify_on_failure: bool = True


class OrganizeConfigUpdate(BaseModel):
    """更新整理配置Schema"""

    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    library_root: Optional[str] = None
    dir_template: Optional[str] = None
    filename_template: Optional[str] = None
    organize_mode: Optional[str] = None
    generate_nfo: Optional[bool] = None
    nfo_format: Optional[str] = None
    download_poster: Optional[bool] = None
    download_backdrop: Optional[bool] = None
    organize_subtitles: Optional[bool] = None
    skip_existed: Optional[bool] = None
    description: Optional[str] = None


class OrganizeConfigResponse(OrganizeConfigBase):
    """整理配置响应Schema"""

    id: int

    # NFO和元数据配置
    generate_nfo: bool
    nfo_format: str
    download_poster: bool
    download_backdrop: bool
    poster_filename: str
    backdrop_filename: str

    # 字幕配置
    organize_subtitles: bool
    subtitle_filename_template: Optional[str] = None

    # 文件过滤
    min_file_size_mb: Optional[int] = None
    max_file_size_mb: Optional[int] = None
    include_extensions: Optional[List[str]] = None
    exclude_extensions: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None

    # 高级选项
    skip_existed: bool
    overwrite_nfo: bool
    overwrite_poster: bool
    overwrite_backdrop: bool

    # 字幕下载
    auto_download_subtitle: bool
    subtitle_languages: Optional[List[str]] = None

    # 通知配置
    notify_on_success: bool
    notify_on_failure: bool

    # 统计信息
    total_organized_count: int
    last_organized_at: Optional[datetime] = None

    # 时间信息
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizeConfigListResponse(BaseModel):
    """整理配置列表响应Schema"""

    total: int
    items: List[OrganizeConfigResponse]
