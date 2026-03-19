# -*- coding: utf-8 -*-
"""
统一电影资源Schema
"""
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class UnifiedMovieBase(BaseModel):
    """统一电影资源基础Schema"""

    # 标识
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    douban_id: Optional[str] = None

    # 标题
    title: str
    original_title: Optional[str] = None
    aka: Optional[List[str]] = None

    # 基础信息
    year: Optional[int] = None
    release_date: Optional[date] = None
    runtime: Optional[int] = None

    # 评分
    rating_tmdb: Optional[Decimal] = None
    votes_tmdb: Optional[int] = None
    rating_douban: Optional[Decimal] = None
    votes_douban: Optional[int] = None
    rating_imdb: Optional[Decimal] = None
    votes_imdb: Optional[int] = None

    # 分类/标签
    genres: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    countries: Optional[List[str]] = None

    # 人员
    directors: Optional[List[dict]] = None
    actors: Optional[List[dict]] = None
    writers: Optional[List[dict]] = None

    # 内容描述
    overview: Optional[str] = None
    tagline: Optional[str] = None

    # 分级/系列
    certification: Optional[str] = None
    collection_id: Optional[int] = None
    collection_name: Optional[str] = None

    # 制作信息
    budget: Optional[int] = None
    revenue: Optional[int] = None
    production_companies: Optional[List[dict]] = None
    status: Optional[str] = None

    # 图片
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    logo_url: Optional[str] = None
    clearart_url: Optional[str] = None
    banner_url: Optional[str] = None

    # 元数据管理
    metadata_source: Optional[str] = None


class UnifiedMovieCreate(UnifiedMovieBase):
    """创建统一电影资源Schema"""
    pass


class UnifiedMovieUpdate(BaseModel):
    """更新统一电影资源Schema"""

    # 外部ID
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    douban_id: Optional[str] = None

    # 标题
    title: Optional[str] = None
    original_title: Optional[str] = None
    aka: Optional[List[str]] = None

    # 基础信息
    year: Optional[int] = None
    release_date: Optional[date] = None
    runtime: Optional[int] = None

    # 评分
    rating_tmdb: Optional[Decimal] = None
    votes_tmdb: Optional[int] = None
    rating_douban: Optional[Decimal] = None
    votes_douban: Optional[int] = None
    rating_imdb: Optional[Decimal] = None
    votes_imdb: Optional[int] = None

    # 分类/标签
    genres: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    countries: Optional[List[str]] = None

    # 内容描述
    overview: Optional[str] = None
    tagline: Optional[str] = None

    # 分级
    certification: Optional[str] = None

    # 图片
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class UnifiedMovieResponse(UnifiedMovieBase):
    """统一电影资源响应Schema"""

    id: int

    # PT资源统计
    pt_resource_count: int = 0
    has_free_resource: bool = False
    best_quality: Optional[str] = None
    best_seeder_count: int = 0
    last_resource_updated_at: Optional[datetime] = None

    # 本地文件
    local_file_count: int = 0
    has_local: bool = False
    local_images_dir: Optional[str] = None

    # 详情加载状态
    detail_loaded: bool = False
    detail_loaded_at: Optional[datetime] = None

    # 时间戳
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class UnifiedMovieListResponse(BaseModel):
    """统一电影资源列表响应Schema（精简版，用于卡片展示）"""

    id: int

    # 基础信息
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None

    # 评分（只保留常用的）
    rating_tmdb: Optional[Decimal] = None
    rating_douban: Optional[Decimal] = None

    # 分类
    genres: Optional[List[str]] = None

    # 图片（只要海报）
    poster_url: Optional[str] = None

    # PT资源统计
    pt_resource_count: int = 0
    has_free_resource: bool = False
    best_quality: Optional[str] = None
    best_seeder_count: int = 0

    # 本地文件
    has_local: bool = False

    # 时间戳
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class UnifiedMovieWithPTResources(UnifiedMovieResponse):
    """统一电影资源（含PT资源列表）Schema"""

    pt_resources: List[dict] = Field(default_factory=list, description="关联的PT资源列表")
