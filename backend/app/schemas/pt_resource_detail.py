# -*- coding: utf-8 -*-
"""
PT资源详情Schema
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class PTResourceDetailBase(BaseModel):
    """PT资源详情基础Schema"""
    description: Optional[str] = None
    mediainfo: Optional[str] = None
    nfo: Optional[str] = None
    dmm_product_number: Optional[str] = None
    dmm_director: Optional[str] = None
    dmm_series: Optional[str] = None
    dmm_maker: Optional[str] = None
    dmm_label: Optional[str] = None
    dmm_actress_list: Optional[List[str]] = None
    dmm_keyword_list: Optional[List[str]] = None
    origin_file_name: Optional[str] = None
    thank_count: Optional[int] = None
    comment_count: Optional[int] = None
    view_count: Optional[int] = None
    hit_count: Optional[int] = None
    detail_loaded: bool = False
    detail_loaded_at: Optional[datetime] = None


class PTResourceDetailResponse(PTResourceDetailBase):
    """PT资源详情响应Schema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    pt_resource_id: int
    created_at: datetime
    updated_at: datetime


class PTResourceDetailItemBase(BaseModel):
    """PT资源详情列表项基础Schema - 用于列表展示"""
    id: int
    title: str
    subtitle: Optional[str] = None
    poster_url: Optional[str] = Field(None, alias="posterUrl")
    image_list: List[str] = Field(default_factory=list, alias="imageList")
    published_at: Optional[datetime] = Field(None, alias="publishedAt")
    size_bytes: int = Field(..., alias="sizeBytes")
    seeders: int
    leechers: int
    is_free: bool = Field(..., alias="isFree")
    promotion_type: Optional[str] = Field(None, alias="promotionType")
    detail_url: Optional[str] = Field(None, alias="detailUrl")
    download_url: Optional[str] = Field(None, alias="downloadUrl")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class PTResourceDetailItemResponse(PTResourceDetailItemBase):
    """PT资源详情项响应Schema - 用于详情页"""
    detail_loaded: bool = Field(default=False, alias="detailLoaded")

    # 详情数据（如果已加载）
    description: Optional[str] = None
    mediainfo: Optional[str] = None
    dmm_info: Optional[dict[str, Any]] = Field(None, alias="dmmInfo")


class PTResourceDetailListResponse(BaseModel):
    """PT资源详情列表响应Schema"""
    items: List[PTResourceDetailItemBase]
    total: int
    page: int
    page_size: int
