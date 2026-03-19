# -*- coding: utf-8 -*-
"""
资源映射关系Schema - 多态关联设计
"""
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class ResourceMappingBase(BaseModel):
    """资源映射关系基础Schema"""

    pt_resource_id: int
    media_type: str = Field(..., description="媒体类型：movie/tv/music/book/anime/adult")

    # 多态关联字段
    unified_table_name: str = Field(..., description="统一资源表名：unified_movies/unified_tv/unified_music/...")
    unified_resource_id: int = Field(..., description="统一资源ID")

    # 匹配信息
    match_method: Optional[str] = Field(None, description="匹配方式：id_exact/title_year/title_fuzzy/manual")
    match_confidence: Optional[int] = Field(None, ge=0, le=100, description="匹配置信度 0-100")
    match_score_detail: Optional[dict] = None

    # 推荐度
    is_primary: bool = Field(default=False, description="是否主推荐资源")
    # recommendation_score: Optional[int] = Field(None, ge=0, le=100, description="推荐度评分 0-100")
    # recommendation_reason: Optional[dict] = None

    # 人工确认
    # is_verified: bool = False
    # verified_by: Optional[int] = None


class ResourceMappingCreate(ResourceMappingBase):
    """创建资源映射关系Schema"""
    pass


class ResourceMappingUpdate(BaseModel):
    """更新资源映射关系Schema"""

    is_primary: Optional[bool] = None
    recommendation_score: Optional[int] = Field(None, ge=0, le=100)
    recommendation_reason: Optional[dict] = None
    is_verified: Optional[bool] = None


class ResourceMappingResponse(ResourceMappingBase):
    """资源映射关系响应Schema"""

    id: int
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceMappingWithDetails(ResourceMappingResponse):
    """资源映射关系（含详细信息）Schema"""

    pt_resource: Optional[dict] = Field(None, description="PT资源详情")
    unified_resource: Optional[Any] = Field(None, description="统一资源详情（根据unified_table_name动态加载）")
