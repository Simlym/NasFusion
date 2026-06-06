# -*- coding: utf-8 -*-
"""
系统信息 API（版本、更新检查）
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.common import version_service

router = APIRouter(prefix="/system", tags=["系统信息"])


class VersionInfo(BaseModel):
    current: str
    latest: Optional[str] = None
    has_update: bool = False
    release_url: str


@router.get("/version", response_model=VersionInfo)
async def get_version():
    """
    获取当前版本及更新信息。

    - **current**: 当前运行版本（镜像构建时由 Git tag 注入）
    - **latest**: GitHub 最新发布版本（外网不可达时为 null）
    - **has_update**: 是否有可用更新
    - **release_url**: 最新版本发布页

    该接口公开（登录页也可展示版本号）；最新版本查询结果在后端缓存 6 小时。
    """
    return await version_service.get_version_info()


@router.post("/version/check", response_model=VersionInfo)
async def check_version(
    force: bool = Query(False, description="是否强制跳过缓存，立即向 GitHub 查询"),
    current_user: User = Depends(get_current_active_user),
):
    """
    主动检查更新（需登录）。force=true 时跳过缓存立即查询 GitHub。
    """
    return await version_service.get_version_info(force=force)
