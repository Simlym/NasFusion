# -*- coding: utf-8 -*-
"""
存储挂载点 Schema 定义
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class StorageMountBase(BaseModel):
    """存储挂载点基础 Schema"""
    name: str = Field(..., description="挂载点名称")
    mount_type: str = Field(..., description="挂载点类型: download/library")
    container_path: str = Field(..., description="容器内路径")
    host_path: Optional[str] = Field(None, description="宿主机路径")


class StorageMountCreate(StorageMountBase):
    """创建存储挂载点请求"""
    media_category: Optional[str] = Field(None, description="媒体分类 (仅 library 类型)")
    is_default: bool = Field(False, description="是否为默认挂载点")


class StorageMountUpdate(BaseModel):
    """更新存储挂载点请求"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="挂载点名称")
    container_path: Optional[str] = Field(None, description="容器内路径")
    host_path: Optional[str] = Field(None, description="宿主机路径")
    media_category: Optional[str] = Field(None, description="媒体分类")
    priority: Optional[int] = Field(None, ge=0, le=1000, description="优先级")
    is_default: Optional[bool] = Field(None, description="是否为默认")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    custom_label: Optional[str] = Field(None, max_length=100, description="自定义标签")
    description: Optional[str] = Field(None, description="备注")
    disk_group: Optional[str] = Field(None, max_length=50, description="磁盘组")


class StorageMountResponse(StorageMountBase):
    """存储挂载点响应"""
    id: int
    device_id: Optional[int] = Field(None, description="设备ID")
    disk_group: Optional[str] = Field(None, description="磁盘组")
    media_category: Optional[str] = Field(None, description="媒体分类")
    priority: int = Field(0, description="优先级")
    is_default: bool = Field(False, description="是否为默认")
    is_enabled: bool = Field(True, description="是否启用")
    is_accessible: bool = Field(True, description="是否可访问")
    total_space: Optional[int] = Field(None, description="总空间(字节)")
    used_space: Optional[int] = Field(None, description="已用空间(字节)")
    free_space: Optional[int] = Field(None, description="可用空间(字节)")
    usage_percent: Optional[float] = Field(None, description="使用率(%)")
    custom_label: Optional[str] = Field(None, description="自定义标签")
    description: Optional[str] = Field(None, description="备注")
    last_scan_at: Optional[datetime] = Field(None, description="最后扫描时间")
    created_at: datetime
    updated_at: datetime
    # 动态属性 (查询时可能添加)
    is_same_disk: Optional[bool] = Field(None, description="是否与目标同盘")

    class Config:
        from_attributes = True


class StorageMountListResponse(BaseModel):
    """存储挂载点列表响应"""
    total: int = Field(..., description="总数")
    items: List[StorageMountResponse] = Field(..., description="挂载点列表")


class DownloadMountRecommendation(BaseModel):
    """下载挂载点推荐响应"""
    mounts: List[StorageMountResponse] = Field(..., description="推荐的下载挂载点列表")
    target_library_mount: Optional[StorageMountResponse] = Field(None, description="目标媒体库挂载点")


class SameDiskCheckRequest(BaseModel):
    """同盘检测请求"""
    path1: str = Field(..., description="第一个路径")
    path2: str = Field(..., description="第二个路径")


class SameDiskCheckResponse(BaseModel):
    """同盘检测响应"""
    same_disk: bool = Field(..., description="是否同盘")
    can_hardlink: bool = Field(..., description="是否支持硬链接")
    device_id_1: Optional[int] = Field(None, description="路径1的设备ID")
    device_id_2: Optional[int] = Field(None, description="路径2的设备ID")
    reason: Optional[str] = Field(None, description="原因说明")


class ScanMountsResponse(BaseModel):
    """扫描挂载点响应"""
    count: int = Field(..., description="扫描到的挂载点数量")
    message: str = Field(..., description="扫描结果消息")


class RefreshDiskInfoRequest(BaseModel):
    """刷新磁盘信息请求"""
    mount_id: Optional[int] = Field(None, description="挂载点ID, 不指定则刷新所有")


class RefreshDiskInfoResponse(BaseModel):
    """刷新磁盘信息响应"""
    count: int = Field(..., description="刷新的挂载点数量")


class StorageStatsResponse(BaseModel):
    """存储统计响应"""
    total_mounts: int = Field(..., description="总挂载点数")
    download_mounts: int = Field(..., description="下载挂载点数")
    library_mounts: int = Field(..., description="媒体库挂载点数")
    total_space: int = Field(..., description="总空间(字节)")
    used_space: int = Field(..., description="已用空间(字节)")
    free_space: int = Field(..., description="可用空间(字节)")
    accessible_mounts: int = Field(..., description="可访问挂载点数")
    inaccessible_mounts: int = Field(..., description="不可访问挂载点数")
