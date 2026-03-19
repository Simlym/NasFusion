# -*- coding: utf-8 -*-
"""
系统设置API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.system_setting import (
    SystemSettingCreate,
    SystemSettingUpdate,
    SystemSettingResponse,
    SystemSettingList,
)
from app.services.common.system_setting_service import SystemSettingService
from app.services.identification.identify_priority_service import IdentificationPriorityService

router = APIRouter(prefix="/system-settings", tags=["系统设置"])


@router.get("", response_model=SystemSettingList)
async def get_settings(
    category: Optional[str] = Query(None, description="设置分类（可选）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取系统设置列表

    - **category**: 可选，按分类筛选
    """
    if category:
        settings = await SystemSettingService.get_by_category(db, category)
    else:
        settings = await SystemSettingService.get_all(db)

    return SystemSettingList(
        total=len(settings),
        items=[SystemSettingResponse.model_validate(s) for s in settings],
    )


@router.get("/{category}/{key}", response_model=SystemSettingResponse)
async def get_setting(
    category: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取单个系统设置

    - **category**: 设置分类
    - **key**: 设置键
    """
    setting = await SystemSettingService.get_by_key(db, category, key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"设置不存在: {category}/{key}")

    return SystemSettingResponse.model_validate(setting)


@router.post("", response_model=SystemSettingResponse)
async def create_setting(
    setting_data: SystemSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建系统设置

    如果设置已存在，返回409错误
    """
    # 检查是否已存在
    existing = await SystemSettingService.get_by_key(db, setting_data.category, setting_data.key)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"设置已存在: {setting_data.category}/{setting_data.key}"
        )

    setting = await SystemSettingService.create(db, setting_data)
    return SystemSettingResponse.model_validate(setting)


@router.put("/{category}/{key}", response_model=SystemSettingResponse)
async def update_setting(
    category: str,
    key: str,
    setting_data: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新系统设置

    - **category**: 设置分类
    - **key**: 设置键
    """
    setting = await SystemSettingService.update(db, category, key, setting_data)
    if not setting:
        raise HTTPException(status_code=404, detail=f"设置不存在: {category}/{key}")

    # 如果更新的是识别优先级配置，清除缓存
    if category == "metadata_scraping" and key == "identification_priority":
        IdentificationPriorityService.clear_cache()

    return SystemSettingResponse.model_validate(setting)


@router.post("/{category}/{key}/upsert", response_model=SystemSettingResponse)
async def upsert_setting(
    category: str,
    key: str,
    value: str = Query(..., description="设置值"),
    description: Optional[str] = Query(None, description="设置描述"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建或更新设置（Upsert）

    如果设置存在则更新，不存在则创建

    - **category**: 设置分类
    - **key**: 设置键
    - **value**: 设置值
    - **description**: 设置描述（可选）
    """
    setting = await SystemSettingService.upsert(db, category, key, value, description)

    # 如果更新的是识别优先级配置，清除缓存
    if category == "metadata_scraping" and key == "identification_priority":
        IdentificationPriorityService.clear_cache()

    return SystemSettingResponse.model_validate(setting)


@router.delete("/{category}/{key}")
async def delete_setting(
    category: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除系统设置

    - **category**: 设置分类
    - **key**: 设置键
    """
    success = await SystemSettingService.delete(db, category, key)
    if not success:
        raise HTTPException(status_code=404, detail=f"设置不存在: {category}/{key}")

    return {"success": True, "message": "设置已删除"}
