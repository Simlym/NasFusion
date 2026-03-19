# -*- coding: utf-8 -*-
"""
图片代理API
提供图片缓存代理服务，包括获取图片、缓存统计和清理功能
"""
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.common.image_cache_service import ImageCacheService

router = APIRouter(prefix="/image-cache", tags=["图片缓存"])


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""

    total_count: int = Field(description="总缓存数量")
    total_size_bytes: int = Field(description="总大小（字节）")
    total_size_mb: float = Field(description="总大小（MB）")
    unique_file_count: int = Field(description="唯一文件数量（去重后）")
    source_stats: dict = Field(description="按来源类型统计")
    cache_directory: str = Field(description="缓存目录路径")


class CacheCleanRequest(BaseModel):
    """缓存清理请求"""

    mode: str = Field(
        default="unused",
        description="清理模式: expired(过期), oldest(最旧), unused(未使用), all(全部)",
    )
    keep_days: int = Field(default=30, ge=0, description="保留最近N天的缓存")
    keep_size_mb: int = Field(default=1000, ge=0, description="保留最多N MB的缓存")


class CacheCleanResponse(BaseModel):
    """缓存清理响应"""

    mode: str = Field(description="清理模式")
    deleted_count: int = Field(description="删除的记录数")
    deleted_size_bytes: int = Field(description="删除的大小（字节）")
    deleted_size_mb: float = Field(description="删除的大小（MB）")
    deleted_files: int = Field(description="删除的文件数")


class CacheSettingsRequest(BaseModel):
    """缓存设置请求"""

    expire_days: int = Field(default=0, ge=0, description="过期天数（0=永不过期）")
    max_size_mb: int = Field(default=0, ge=0, description="最大缓存大小MB（0=无限制）")


class CacheSettingsResponse(BaseModel):
    """缓存设置响应"""

    expire_days: int = Field(description="过期天数（0=永不过期）")
    max_size_mb: int = Field(description="最大缓存大小MB（0=无限制）")


@router.get("/fetch", summary="获取代理图片")
async def get_proxied_image(
    url: str = Query(..., description="原始图片URL（URL编码）"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取代理图片

    - 如果图片已缓存，直接返回本地文件
    - 如果未缓存，先下载并缓存，然后返回
    - 支持TMDB、豆瓣等外部图片源

    **注意**：此接口不需要认证，以便前端img标签直接使用
    """
    # URL解码
    decoded_url = unquote(url)

    if not decoded_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="无效的图片URL")

    # 尝试获取或下载缓存
    cache = await ImageCacheService.download_and_cache(db, decoded_url)

    if not cache:
        raise HTTPException(status_code=502, detail="无法下载图片")

    # 获取文件路径
    file_path = ImageCacheService.get_file_path(cache)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="缓存文件不存在")

    # 返回文件
    return FileResponse(
        path=str(file_path),
        media_type=cache.content_type,
        headers={
            "Cache-Control": "public, max-age=31536000",  # 缓存1年
            "X-Cache-Hit": "true",
        },
    )


@router.get("/stats", response_model=CacheStatsResponse, summary="获取缓存统计")
async def get_cache_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取图片缓存统计信息

    包括：
    - 总缓存数量和大小
    - 按来源类型统计
    - 唯一文件数量（去重后）
    - 缓存目录路径
    """
    stats = await ImageCacheService.get_cache_stats(db)
    return CacheStatsResponse(**stats)


@router.post("/clean", response_model=CacheCleanResponse, summary="清理缓存")
async def clean_cache(
    request: CacheCleanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    手动清理图片缓存

    清理模式：
    - **expired**: 清理创建时间超过keep_days的缓存
    - **unused**: 清理最后访问时间超过keep_days的缓存
    - **oldest**: 保留最近访问的缓存，删除超出keep_size_mb的部分
    - **all**: 清理全部缓存（谨慎使用）
    """
    result = await ImageCacheService.clean_cache(
        db,
        mode=request.mode,
        keep_days=request.keep_days,
        keep_size_mb=request.keep_size_mb,
    )
    return CacheCleanResponse(**result)


@router.delete("/{cache_id}", summary="删除单个缓存")
async def delete_single_cache(
    cache_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除单个图片缓存记录

    - **cache_id**: 缓存记录ID
    """
    success = await ImageCacheService.delete_single_cache(db, cache_id)

    if not success:
        raise HTTPException(status_code=404, detail="缓存记录不存在")

    return {"message": "缓存已删除", "cache_id": cache_id}


@router.get("/settings", response_model=CacheSettingsResponse, summary="获取缓存设置")
async def get_cache_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取图片缓存设置

    设置存储在system_settings表中
    """
    from app.services.common.system_setting_service import SystemSettingService

    # 获取过期天数设置
    expire_setting = await SystemSettingService.get_by_key(db, "image_cache", "expire_days")
    expire_days = int(expire_setting.value) if expire_setting else 0

    # 获取最大大小设置
    max_size_setting = await SystemSettingService.get_by_key(db, "image_cache", "max_size_mb")
    max_size_mb = int(max_size_setting.value) if max_size_setting else 0

    return CacheSettingsResponse(expire_days=expire_days, max_size_mb=max_size_mb)


@router.put("/settings", response_model=CacheSettingsResponse, summary="更新缓存设置")
async def update_cache_settings(
    settings: CacheSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新图片缓存设置

    - **expire_days**: 过期天数（0=永不过期）
    - **max_size_mb**: 最大缓存大小（0=无限制）
    """
    from app.services.common.system_setting_service import SystemSettingService

    # 更新或创建过期天数设置
    await SystemSettingService.upsert(
        db,
        category="image_cache",
        key="expire_days",
        value=str(settings.expire_days),
        description="图片缓存过期天数（0=永不过期）",
    )

    # 更新或创建最大大小设置
    await SystemSettingService.upsert(
        db,
        category="image_cache",
        key="max_size_mb",
        value=str(settings.max_size_mb),
        description="图片缓存最大大小MB（0=无限制）",
    )

    return CacheSettingsResponse(
        expire_days=settings.expire_days, max_size_mb=settings.max_size_mb
    )
