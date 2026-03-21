# -*- coding: utf-8 -*-
"""
文件系统相关的 Pydantic Schema
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class DiskInfo(BaseModel):
    """磁盘信息"""
    total: int = Field(..., description="总空间（字节）")
    used: int = Field(..., description="已使用空间（字节）")
    free: int = Field(..., description="可用空间（字节）")
    percent: float = Field(..., description="使用百分比")


class PathValidationResponse(BaseModel):
    """路径验证响应"""
    exists: bool = Field(..., description="路径是否存在")
    is_directory: bool = Field(..., description="是否是目录")
    readable: bool = Field(..., description="是否可读")
    writable: bool = Field(..., description="是否可写")
    disk_info: Optional[DiskInfo] = Field(None, description="磁盘信息")
    error: Optional[str] = Field(None, description="错误信息")


class DirectoryItem(BaseModel):
    """目录项"""
    name: str = Field(..., description="目录名称")
    path: str = Field(..., description="完整路径")
    size: int = Field(..., description="大小（字节）")
    modified_at: Optional[str] = Field(None, description="修改时间（ISO 8601）")
    is_accessible: bool = Field(..., description="是否可访问")


class BrowseDirectoryResponse(BaseModel):
    """浏览目录响应"""
    current_path: str = Field(..., description="当前路径")
    parent_path: Optional[str] = Field(None, description="父目录路径")
    directories: List[DirectoryItem] = Field(default_factory=list, description="子目录列表")


class CreateDirectoryRequest(BaseModel):
    """创建目录请求"""
    path: str = Field(..., description="目录路径")
    recursive: bool = Field(True, description="是否递归创建父目录")


class CreateDirectoryResponse(BaseModel):
    """创建目录响应"""
    success: bool = Field(..., description="是否成功")
    path: str = Field(..., description="目录路径")
    created: bool = Field(..., description="是否新创建（false表示已存在）")
    error: Optional[str] = Field(None, description="错误信息")


class PermissionsResponse(BaseModel):
    """权限检查响应"""
    readable: bool = Field(..., description="是否可读")
    writable: bool = Field(..., description="是否可写")
    executable: bool = Field(..., description="是否可执行")


class DefaultBrowsePathResponse(BaseModel):
    """默认浏览路径响应"""
    is_docker: bool = Field(..., description="是否Docker环境")
    default_path: str = Field(..., description="默认浏览起始路径")
