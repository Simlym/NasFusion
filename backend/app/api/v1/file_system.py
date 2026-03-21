# -*- coding: utf-8 -*-
"""
文件系统 API 路由
提供路径验证、目录浏览、磁盘信息等功能
"""
from typing import List
from fastapi import APIRouter, Depends, Query, Body, HTTPException

from app.models.user import User
from app.core.dependencies import get_current_admin_user
from app.services.common.file_system_service import FileSystemService
from app.schemas.file_system import (
    PathValidationResponse,
    BrowseDirectoryResponse,
    DiskInfo,
    CreateDirectoryRequest,
    CreateDirectoryResponse,
    PermissionsResponse,
    DefaultBrowsePathResponse,
)
from app.services.storage.storage_mount_service import StorageMountService
from app.core.config import settings

router = APIRouter(prefix="/file-system", tags=["文件系统"])


@router.post("/validate-path", response_model=PathValidationResponse)
async def validate_path(
    path: str = Body(..., embed=True, description="路径字符串"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    验证路径有效性

    检查路径是否存在、是否是目录、权限、磁盘空间等信息
    """
    result = await FileSystemService.validate_path(path)
    return result


@router.get("/browse-directory", response_model=BrowseDirectoryResponse)
async def browse_directory(
    path: str = Query(..., description="目录路径"),
    show_hidden: bool = Query(False, description="是否显示隐藏文件"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    浏览目录结构

    返回指定目录下的所有子目录列表
    """
    try:
        result = await FileSystemService.browse_directory(path, show_hidden)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"浏览目录失败: {str(e)}")


@router.get("/disk-info")
async def get_disk_info(
    paths: List[str] = Query(..., description="路径列表"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    批量获取磁盘信息

    返回每个路径的磁盘使用情况
    """
    result = {}
    for path in paths:
        disk_info = await FileSystemService.get_disk_info(path)
        result[path] = disk_info

    return result


@router.post("/create-directory", response_model=CreateDirectoryResponse)
async def create_directory(
    request: CreateDirectoryRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    创建目录

    支持递归创建父目录
    """
    result = await FileSystemService.create_directory(
        request.path,
        request.recursive
    )
    return result


@router.get("/default-browse-path", response_model=DefaultBrowsePathResponse)
async def get_default_browse_path(
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取默认目录浏览起始路径

    Docker 环境返回 VOLUME_MOUNTS_BASE（卷挂载基础目录），本地环境返回 /
    """
    is_docker = StorageMountService.is_docker_environment()
    default_path = settings.VOLUME_MOUNTS_BASE if is_docker else "/"
    return DefaultBrowsePathResponse(
        is_docker=is_docker,
        default_path=default_path,
    )


@router.get("/check-permissions", response_model=PermissionsResponse)
async def check_permissions(
    path: str = Query(..., description="路径字符串"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    检查目录权限

    返回读、写、执行权限状态
    """
    result = await FileSystemService.check_permissions(path)
    return result
