# -*- coding: utf-8 -*-
"""
存储挂载点 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.services.storage.storage_mount_service import StorageMountService
from app.schemas.storage_mount import (
    StorageMountResponse,
    StorageMountCreate,
    StorageMountUpdate,
    StorageMountListResponse,
    DownloadMountRecommendation,
    SameDiskCheckRequest,
    SameDiskCheckResponse,
    ScanMountsResponse,
    RefreshDiskInfoRequest,
    RefreshDiskInfoResponse,
    StorageStatsResponse,
)

router = APIRouter(prefix="/storage-mounts", tags=["storage_mounts"])


@router.get("", response_model=StorageMountListResponse)
async def list_storage_mounts(
    mount_type: Optional[str] = Query(None, description="挂载点类型: download/library"),
    media_category: Optional[str] = Query(None, description="媒体分类"),
    is_enabled: bool = Query(True, description="是否只返回启用的挂载点"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取存储挂载点列表
    
    - **mount_type**: 可选筛选，download 或 library
    - **media_category**: 可选筛选媒体分类
    - **is_enabled**: 是否只返回启用的挂载点
    """
    mounts = await StorageMountService.get_all_mounts(
        db,
        mount_type=mount_type,
        media_category=media_category,
        is_enabled=is_enabled,
    )
    
    return StorageMountListResponse(
        total=len(mounts),
        items=[StorageMountResponse.model_validate(m) for m in mounts]
    )


@router.get("/download-mounts", response_model=DownloadMountRecommendation)
async def get_download_mounts_for_media(
    media_category: str = Query(..., description="目标媒体分类"),
    target_library_mount_id: Optional[int] = Query(None, description="目标媒体库挂载点ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取推荐的下载挂载点
    
    根据目标媒体分类返回推荐的下载挂载点列表，优先返回与目标媒体库同盘的挂载点
    """
    mounts = await StorageMountService.get_download_mounts_for_media(
        db,
        media_category=media_category,
        target_library_mount_id=target_library_mount_id,
    )
    
    # 获取目标媒体库挂载点信息
    target_library = None
    if target_library_mount_id:
        target_library = await StorageMountService.get_mount_by_id(db, target_library_mount_id)
    
    return DownloadMountRecommendation(
        mounts=[StorageMountResponse.model_validate(m) for m in mounts],
        target_library_mount=StorageMountResponse.model_validate(target_library) if target_library else None
    )


@router.get("/library-mounts")
async def get_library_mounts_by_category(
    media_category: str = Query(..., description="媒体分类"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定分类的媒体库挂载点
    """
    mounts = await StorageMountService.get_library_mounts_by_category(
        db,
        media_category=media_category,
    )
    
    return {
        "mounts": [StorageMountResponse.model_validate(m) for m in mounts]
    }


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取存储统计信息
    """
    all_mounts = await StorageMountService.get_all_mounts(db, is_enabled=False)
    
    download_mounts = [m for m in all_mounts if m.mount_type == "download"]
    library_mounts = [m for m in all_mounts if m.mount_type == "library"]
    accessible_mounts = [m for m in all_mounts if m.is_accessible]
    
    # 计算总空间 (去重设备)
    device_spaces = {}
    for mount in all_mounts:
        if mount.device_id and mount.total_space:
            if mount.device_id not in device_spaces:
                device_spaces[mount.device_id] = {
                    "total": mount.total_space,
                    "used": mount.used_space or 0,
                    "free": mount.free_space or 0,
                }
    
    total_space = sum(d["total"] for d in device_spaces.values())
    used_space = sum(d["used"] for d in device_spaces.values())
    free_space = sum(d["free"] for d in device_spaces.values())
    
    return StorageStatsResponse(
        total_mounts=len(all_mounts),
        download_mounts=len(download_mounts),
        library_mounts=len(library_mounts),
        total_space=total_space,
        used_space=used_space,
        free_space=free_space,
        accessible_mounts=len(accessible_mounts),
        inaccessible_mounts=len(all_mounts) - len(accessible_mounts),
    )


@router.get("/{mount_id}", response_model=StorageMountResponse)
async def get_storage_mount(
    mount_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定挂载点详情
    """
    mount = await StorageMountService.get_mount_by_id(db, mount_id)
    if not mount:
        raise HTTPException(status_code=404, detail="挂载点不存在")
    
    return StorageMountResponse.model_validate(mount)


@router.patch("/{mount_id}", response_model=StorageMountResponse)
async def update_storage_mount(
    mount_id: int,
    data: StorageMountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新挂载点配置
    """
    update_data = data.model_dump(exclude_unset=True)
    mount = await StorageMountService.update_mount_config(db, mount_id, **update_data)
    
    if not mount:
        raise HTTPException(status_code=404, detail="挂载点不存在")
    
    return StorageMountResponse.model_validate(mount)


@router.post("/scan", response_model=ScanMountsResponse)
async def scan_storage_mounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    扫描并初始化存储挂载点
    
    根据运行环境自动选择扫描模式：
    - Docker 模式：扫描预定义的 mount_* 目录
    - 本地模式：从环境变量读取配置
    """
    count = await StorageMountService.scan_and_init_mounts(db)
    
    mode = "Docker" if StorageMountService.is_docker_environment() else "本地"
    
    return ScanMountsResponse(
        count=count,
        message=f"{mode}模式扫描完成，发现 {count} 个挂载点"
    )


@router.post("/refresh-disk-info", response_model=RefreshDiskInfoResponse)
async def refresh_disk_info(
    request: RefreshDiskInfoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刷新挂载点磁盘空间信息
    
    如果不指定 mount_id，则刷新所有挂载点
    """
    count = await StorageMountService.refresh_disk_info(db, mount_id=request.mount_id)
    
    return RefreshDiskInfoResponse(count=count)


@router.post("/check-same-disk", response_model=SameDiskCheckResponse)
async def check_same_disk(
    request: SameDiskCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """
    检查两个路径是否在同一磁盘

    用于判断是否可以使用硬链接
    """
    result = StorageMountService.check_same_disk(request.path1, request.path2)

    return SameDiskCheckResponse(**result)


@router.post("", response_model=StorageMountResponse, status_code=201)
async def create_storage_mount(
    data: StorageMountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动创建存储挂载点

    用于添加自定义的下载目录或媒体库目录
    """
    try:
        mount = await StorageMountService.create_mount(
            db,
            name=data.name,
            mount_type=data.mount_type,
            container_path=data.container_path,
            host_path=data.host_path,
            media_category=data.media_category,
            is_default=data.is_default,
        )
        return StorageMountResponse.model_validate(mount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{mount_id}", status_code=204)
async def delete_storage_mount(
    mount_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除存储挂载点

    删除手动创建的挂载点
    """
    success = await StorageMountService.delete_mount(db, mount_id)
    if not success:
        raise HTTPException(status_code=404, detail="挂载点不存在")
    return None
