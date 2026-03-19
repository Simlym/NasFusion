# -*- coding: utf-8 -*-
"""
榜单API路由
"""
import logging
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.trending_collection import TrendingCollection
from app.schemas.task_execution import TaskExecutionCreate
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.trending import (
    COLLECTION_TYPES,
    COLLECTION_TYPE_DISPLAY_NAMES,
    COLLECTION_TYPE_MEDIA_TYPES,
)
from app.constants.task import TASK_TYPE_TRENDING_SYNC

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trending", tags=["榜单"])


@router.get("/collections/types", summary="获取所有榜单类型")
async def get_collection_types():
    """获取所有可用的榜单类型"""
    return {
        "types": [
            {
                "value": ct,
                "label": COLLECTION_TYPE_DISPLAY_NAMES.get(ct, ct),
                "mediaType": COLLECTION_TYPE_MEDIA_TYPES.get(ct, "movie"),
            }
            for ct in COLLECTION_TYPES
        ]
    }


@router.get("/collections/{collection_type}/ids", summary="获取榜单资源ID列表")
async def get_collection_ids(
    collection_type: str,
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定榜单的资源ID列表（用于前端筛选）

    Args:
        collection_type: 榜单类型
        limit: 返回数量限制
        db: 数据库会话

    Returns:
        榜单资源ID列表
    """
    if collection_type not in COLLECTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的榜单类型: {collection_type}",
        )

    stmt = (
        select(TrendingCollection.unified_resource_id)
        .where(TrendingCollection.collection_type == collection_type)
        .order_by(TrendingCollection.rank_position.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    ids = list(result.scalars().all())

    return {
        "collection_type": collection_type,
        "ids": ids,
        "count": len(ids),
    }


@router.post("/sync", summary="同步榜单")
async def sync_collections(
    collection_types: Optional[List[str]] = None,
    count: int = Query(100, ge=1, le=250),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    同步榜单数据（异步任务）

    Args:
        collection_types: 榜单类型列表（可选，默认全部）
        count: 每个榜单同步数量
        db: 数据库会话
        current_user: 当前用户

    Returns:
        任务执行ID
    """
    collection_types = collection_types or COLLECTION_TYPES

    # 验证榜单类型
    invalid_types = [ct for ct in collection_types if ct not in COLLECTION_TYPES]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的榜单类型: {', '.join(invalid_types)}",
        )

    # 创建任务执行记录
    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_TRENDING_SYNC,
        task_name=f"同步榜单 ({len(collection_types)} 个)",
        handler=TASK_TYPE_TRENDING_SYNC,
        handler_params={
            "collection_types": collection_types,
            "count": count,
        },
        user_id=current_user.id,
    )
    execution = await TaskExecutionService.create(db, execution_data)

    # 后台执行（不阻塞API响应）
    from app.services.task.scheduler_manager import scheduler_manager

    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return {
        "execution_id": execution.id,
        "message": f"榜单同步任务已创建，共 {len(collection_types)} 个榜单",
    }
