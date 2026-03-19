# -*- coding: utf-8 -*-
"""
整理配置API路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.organize_config import (
    OrganizeConfigCreate,
    OrganizeConfigListResponse,
    OrganizeConfigResponse,
    OrganizeConfigUpdate,
)
from app.services.mediafile.organize_config_service import OrganizeConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organize-configs", tags=["organize_configs"])


@router.get("", response_model=OrganizeConfigListResponse)
async def list_organize_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    media_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询整理配置列表

    Args:
        skip: 跳过数量
        limit: 返回数量
        media_type: 媒体类型过滤
        is_enabled: 是否启用过滤
        db: 数据库会话
        current_user: 当前用户

    Returns:
        整理配置列表
    """
    result = await OrganizeConfigService.list(
        db, skip=skip, limit=limit, media_type=media_type, is_enabled=is_enabled
    )
    return result


@router.get("/{config_id}", response_model=OrganizeConfigResponse)
async def get_organize_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取整理配置详情

    Args:
        config_id: 配置ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        整理配置详情
    """
    config = await OrganizeConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.get("/default/{media_type}", response_model=OrganizeConfigResponse)
async def get_default_organize_config(
    media_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取指定媒体类型的默认配置

    Args:
        media_type: 媒体类型
        db: 数据库会话
        current_user: 当前用户

    Returns:
        默认配置
    """
    config = await OrganizeConfigService.get_default(db, media_type)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到媒体类型 {media_type} 的默认配置")
    return config


@router.post("", response_model=OrganizeConfigResponse, status_code=201)
async def create_organize_config(
    config_data: OrganizeConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建整理配置

    Args:
        config_data: 配置数据
        db: 数据库会话
        current_user: 当前用户

    Returns:
        创建的配置
    """
    try:
        config = await OrganizeConfigService.create(db, config_data.model_dump())
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("创建整理配置失败")
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")


@router.post("/init-defaults")
async def init_default_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    初始化默认配置（电影、电视剧、动漫）

    Args:
        db: 数据库会话
        current_user: 当前用户

    Returns:
        创建的配置列表
    """
    try:
        configs = await OrganizeConfigService.create_default_configs(db)
        return {
            "status": "success",
            "message": f"创建了 {len(configs)} 个默认配置",
            "configs": [OrganizeConfigResponse.model_validate(c) for c in configs],
        }
    except Exception as e:
        logger.exception("初始化默认配置失败")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.patch("/{config_id}", response_model=OrganizeConfigResponse)
async def update_organize_config(
    config_id: int,
    config_data: OrganizeConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新整理配置

    Args:
        config_id: 配置ID
        config_data: 配置数据
        db: 数据库会话
        current_user: 当前用户

    Returns:
        更新后的配置
    """
    try:
        config = await OrganizeConfigService.update(
            db, config_id, config_data.model_dump(exclude_unset=True)
        )
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"更新整理配置失败: {config_id}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/{config_id}")
async def delete_organize_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除整理配置

    Args:
        config_id: 配置ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        删除结果
    """
    success = await OrganizeConfigService.delete(db, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在")

    return {"status": "success", "message": "删除成功"}
