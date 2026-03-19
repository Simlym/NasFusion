# -*- coding: utf-8 -*-
"""
媒体目录Schema定义
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MediaDirectoryBase(BaseModel):
    """媒体目录基础Schema"""
    directory_name: str = Field(..., description="目录名称")
    media_type: Optional[str] = Field(None, description="媒体类型")
    unified_table_name: Optional[str] = Field(None, description="统一资源表名")
    unified_resource_id: Optional[int] = Field(None, description="统一资源ID")
    series_name: Optional[str] = Field(None, description="剧集名称")
    season_number: Optional[int] = Field(None, description="季度编号")


class MediaDirectoryCreate(MediaDirectoryBase):
    """创建媒体目录请求"""
    directory_path: str = Field(..., description="目录完整路径")
    parent_id: Optional[int] = Field(None, description="父目录ID")


class MediaDirectoryUpdate(BaseModel):
    """更新媒体目录请求"""
    unified_resource_id: Optional[int] = Field(None, description="统一资源ID")
    series_name: Optional[str] = Field(None, description="剧集名称")
    season_number: Optional[int] = Field(None, description="季度编号")


class MediaDirectoryResponse(MediaDirectoryBase):
    """媒体目录响应"""
    id: int
    directory_path: str
    parent_id: Optional[int]
    episode_count: int = Field(default=0, description="集数统计")
    has_nfo: bool = Field(default=False, description="是否存在NFO")
    nfo_path: Optional[str]
    has_poster: bool = Field(default=False, description="是否存在海报")
    poster_path: Optional[str]
    has_backdrop: bool = Field(default=False, description="是否存在背景图")
    backdrop_path: Optional[str]
    issue_flags: Dict[str, Any] = Field(default_factory=dict, description="问题标记")
    total_files: int = Field(default=0, description="文件总数")
    total_size: int = Field(default=0, description="总大小(字节)")
    scanned_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DirectoryTreeNode(MediaDirectoryResponse):
    """目录树节点(递归结构)"""
    children: List['DirectoryTreeNode'] = Field(default_factory=list, description="子目录列表")
    has_issues: bool = Field(default=False, description="是否有问题")
    subdir_count: int = Field(default=0, description="子目录数量")

    class Config:
        from_attributes = True


class DirectoryStatistics(BaseModel):
    """目录统计信息"""
    total_files: int = Field(..., description="总文件数")
    total_size: int = Field(..., description="总大小(字节)")
    video_files: int = Field(..., description="视频文件数")
    identified_files: int = Field(..., description="已识别文件数")


class DirectoryDetailResponse(BaseModel):
    """目录详情响应"""
    directory: MediaDirectoryResponse
    statistics: DirectoryStatistics
    files: List[Any] = Field(default_factory=list, description="文件列表")
    nfo_data: Optional[Dict[str, Any]] = Field(None, description="NFO解析数据")


class DirectoryTreeQuery(BaseModel):
    """目录树查询参数"""
    media_type: Optional[str] = Field(None, description="媒体类型筛选")
    parent_id: Optional[int] = Field(None, description="父目录ID")
    load_children: bool = Field(False, description="是否预加载子目录")


class SyncFromFilesRequest(BaseModel):
    """从文件同步目录树请求"""
    base_directory: str = Field(..., description="基础目录路径")


class SyncFromFilesResponse(BaseModel):
    """从文件同步目录树响应"""
    created: int = Field(..., description="新建目录数")
    updated: int = Field(..., description="更新目录数")


class DetectIssuesRequest(BaseModel):
    """检测问题请求"""
    directory_id: Optional[int] = Field(None, description="目录ID(None表示检测所有)")
    media_type: Optional[str] = Field(None, description="媒体类型(None表示所有类型)")


class DetectIssuesResponse(BaseModel):
    """检测问题响应"""
    issues: Dict[str, int] = Field(..., description="问题统计")
    total_issues: int = Field(..., description="总问题数")
