# -*- coding: utf-8 -*-
"""
下载器配置API路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.downloader import (
    DownloaderConfigCreate,
    DownloaderConfigListResponse,
    DownloaderConfigResponse,
    DownloaderConfigUpdate,
    DownloaderTestConnectionResponse,
)
from app.services.download.downloader_config_service import DownloaderConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/downloaders", tags=["下载器配置"])


@router.post("", response_model=DownloaderConfigResponse, status_code=201)
async def create_downloader(
    data: DownloaderConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建下载器配置"""
    try:
        config = await DownloaderConfigService.create(db, data)
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating downloader: {str(e)}")
        raise HTTPException(status_code=500, detail="创建下载器配置失败")


@router.get("", response_model=DownloaderConfigListResponse)
async def list_downloaders(
    skip: int = 0,
    limit: int = 100,
    is_enabled: Optional[bool] = None,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取下载器配置列表"""
    result = await DownloaderConfigService.list(
        db, skip=skip, limit=limit, is_enabled=is_enabled, type=type
    )
    return result


@router.get("/{config_id}", response_model=DownloaderConfigResponse)
async def get_downloader(
    config_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取下载器配置详情"""
    config = await DownloaderConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="下载器配置不存在")
    return config


@router.put("/{config_id}", response_model=DownloaderConfigResponse)
async def update_downloader(
    config_id: int,
    data: DownloaderConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新下载器配置"""
    try:
        config = await DownloaderConfigService.update(db, config_id, data)
        if not config:
            raise HTTPException(status_code=404, detail="下载器配置不存在")
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating downloader: {str(e)}")
        raise HTTPException(status_code=500, detail="更新下载器配置失败")


@router.delete("/{config_id}", status_code=204)
async def delete_downloader(
    config_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除下载器配置"""
    success = await DownloaderConfigService.delete(db, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="下载器配置不存在")


@router.post("/{config_id}/test", response_model=DownloaderTestConnectionResponse)
async def test_downloader_connection(
    config_id: int,
    db: AsyncSession = Depends(get_db),
):
    """测试下载器连接"""
    result = await DownloaderConfigService.test_connection(db, config_id)
    return result


@router.get("/default", response_model=DownloaderConfigResponse)
async def get_default_downloader(
    db: AsyncSession = Depends(get_db),
):
    """获取默认下载器配置"""
    config = await DownloaderConfigService.get_default(db)
    if not config:
        raise HTTPException(status_code=404, detail="未设置默认下载器")
    return config
