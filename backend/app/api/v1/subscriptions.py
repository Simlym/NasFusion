# -*- coding: utf-8 -*-
"""
订阅管理API
"""
import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionCreateSchema,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdateSchema,
    SubscriptionCheckLogListResponse,
    EpisodesStatusResponse,
    EpisodeStatusUpdateRequest,
)
from app.services.subscription.subscription_service import SubscriptionService
from app.services.subscription.subscription_check_log_service import SubscriptionCheckLogService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["订阅管理"])


@router.get("", response_model=SubscriptionListResponse, summary="获取订阅列表")
async def get_subscriptions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    media_type: str = Query(None, description="媒体类型过滤: movie/tv"),
    status: str = Query(None, description="状态过滤: active/paused/completed/cancelled"),
    is_active: bool = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取订阅列表

    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **media_type**: 媒体类型过滤（可选）
    - **status**: 状态过滤（可选）
    - **is_active**: 是否激活过滤（可选）
    """
    subscriptions, total = await SubscriptionService.get_list(
        db,
        user_id=current_user.id,
        media_type=media_type,
        status=status,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    return SubscriptionListResponse(
        items=subscriptions,
        total=total,
    )


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建订阅",
)
async def create_subscription(
    subscription_data: SubscriptionCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建新的订阅

    - **media_type**: 媒体类型（movie/tv）
    - **unified_movie_id**: 电影资源ID（movie类型必填）
    - **unified_tv_id**: 电视剧资源ID（tv类型必填）
    - **title**: 订阅标题
    - **current_season**: 订阅的季度（tv类型必填）
    - **start_episode**: 起始集数（tv类型可选，默认1）
    - **rules**: 订阅规则（可选）
    - **auto_download**: 是否自动下载（可选，默认false）
    - 其他配置...
    """
    try:
        subscription = await SubscriptionService.create_subscription(
            db, current_user.id, subscription_data
        )
        return subscription
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{subscription_id}", response_model=SubscriptionResponse, summary="获取订阅详情")
async def get_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取订阅详情"""
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此订阅",
        )

    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse, summary="更新订阅")
async def update_subscription(
    subscription_id: int,
    update_data: SubscriptionUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新订阅配置

    - 可更新任何订阅字段
    - 仅支持更新自己的订阅
    """
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此订阅",
        )

    updated_subscription = await SubscriptionService.update_subscription(
        db, subscription_id, update_data
    )
    return updated_subscription


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除订阅",
)
async def delete_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除订阅"""
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此订阅",
        )

    await SubscriptionService.delete_subscription(db, subscription_id)
    return None


@router.post(
    "/{subscription_id}/pause",
    response_model=SubscriptionResponse,
    summary="暂停订阅",
)
async def pause_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """暂停订阅"""
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订阅",
        )

    updated_subscription = await SubscriptionService.pause_subscription(db, subscription_id)
    return updated_subscription


@router.post(
    "/{subscription_id}/resume",
    response_model=SubscriptionResponse,
    summary="恢复订阅",
)
async def resume_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """恢复订阅"""
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订阅",
        )

    updated_subscription = await SubscriptionService.resume_subscription(db, subscription_id)
    return updated_subscription


@router.post(
    "/{subscription_id}/check",
    summary="手动触发订阅检查",
)
async def check_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发订阅检查"""
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订阅",
        )

    # 动态导入避免循环依赖
    from app.tasks.handlers.subscription_check_handler import SubscriptionCheckHandler

    try:
        result = await SubscriptionCheckHandler.check_subscription(db, subscription_id)
        return {
            "success": True,
            "message": "订阅检查完成",
            "result": result,
        }
    except Exception as e:
        logger.error(f"手动触发订阅检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"订阅检查失败: {str(e)}",
        )


@router.get(
    "/{subscription_id}/check-logs",
    response_model=SubscriptionCheckLogListResponse,
    summary="获取订阅检查日志",
)
async def get_subscription_check_logs(
    subscription_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取订阅的检查日志列表"""
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此订阅",
        )

    logs, total = await SubscriptionCheckLogService.get_list(
        db, subscription_id=subscription_id, page=page, page_size=page_size
    )

    return SubscriptionCheckLogListResponse(
        items=logs,
        total=total,
    )


@router.get(
    "/{subscription_id}/episodes-status",
    response_model=EpisodesStatusResponse,
    summary="获取订阅的集数状态",
)
async def get_episodes_status(
    subscription_id: int,
    refresh: bool = Query(False, description="是否强制刷新状态"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取订阅的集数状态（仅电视剧订阅）

    - **subscription_id**: 订阅ID
    - **refresh**: 是否强制刷新状态（默认false，返回缓存数据）

    返回每集的详细状态：
    - downloaded: 已下载
    - downloading: 下载中
    - available: 有资源可下载
    - waiting: 等待资源
    - failed: 下载失败
    """
    from app.services.subscription.subscription_episode_service import SubscriptionEpisodeService

    # 获取订阅
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此订阅",
        )

    # 检查是否为电视剧订阅
    if not subscription.is_tv_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅电视剧订阅支持集数状态查询",
        )

    # 如果请求刷新或缓存为空，则刷新
    if refresh or not subscription.episodes_status:
        episodes_status = await SubscriptionEpisodeService.refresh_episodes_status(
            db, subscription_id
        )
    else:
        episodes_status = subscription.episodes_status

    # 计算统计信息
    stats = await SubscriptionEpisodeService.get_episodes_status_stats(episodes_status)

    return EpisodesStatusResponse(
        subscription_id=subscription_id,
        season=subscription.current_season,
        start_episode=subscription.start_episode or 1,
        total_episodes=subscription.total_episodes or 0,
        episodes=episodes_status,
        stats=stats,
        last_updated=subscription.updated_at,
    )


@router.post(
    "/{subscription_id}/episodes-status/refresh",
    response_model=EpisodesStatusResponse,
    summary="手动刷新集数状态",
)
async def refresh_episodes_status(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动刷新订阅的集数状态

    强制重新扫描 media_files、download_tasks、pt_resources
    更新所有集数的状态
    """
    from app.services.subscription.subscription_episode_service import SubscriptionEpisodeService

    # 获取订阅
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此订阅",
        )

    # 检查是否为电视剧订阅
    if not subscription.is_tv_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅电视剧订阅支持集数状态查询",
        )

    # 刷新状态
    episodes_status = await SubscriptionEpisodeService.refresh_episodes_status(
        db, subscription_id
    )

    # 计算统计信息
    stats = await SubscriptionEpisodeService.get_episodes_status_stats(episodes_status)

    logger.info(f"手动刷新订阅{subscription_id}集数状态完成")

    return EpisodesStatusResponse(
        subscription_id=subscription_id,
        season=subscription.current_season,
        start_episode=subscription.start_episode or 1,
        total_episodes=subscription.total_episodes or 0,
        episodes=episodes_status,
        stats=stats,
        last_updated=subscription.updated_at,
    )


@router.put(
    "/{subscription_id}/episodes/{episode}/status",
    summary="手动标记集数状态",
)
async def update_episode_status(
    subscription_id: int,
    episode: int,
    body: EpisodeStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动标记某集状态

    - **status**: downloaded / ignored / waiting
    - **note**: 备注（可选）
    """
    from app.services.subscription.subscription_episode_service import SubscriptionEpisodeService
    from app.utils.timezone import now as tz_now

    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订阅",
        )

    if not subscription.is_tv_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅电视剧订阅支持集数状态操作",
        )

    # 构建状态数据
    status_data = {
        "status": body.status,
        "note": body.note or "手动标记",
    }
    if body.status == "downloaded":
        status_data["downloaded_at"] = tz_now()

    await SubscriptionEpisodeService.update_episode_status(
        db, subscription_id, episode, status_data
    )

    logger.info(f"手动标记订阅{subscription_id}第{episode}集为{body.status}")

    return {
        "success": True,
        "message": f"第 {episode} 集已标记为 {body.status}",
        "episode": episode,
        "status": body.status,
    }


@router.post(
    "/{subscription_id}/sync-pt-resources",
    summary="手动同步PT资源",
)
async def sync_subscription_pt_resources(
    subscription_id: int,
    site_id: Optional[int] = Query(None, description="指定PT站点ID"),
    keyword: Optional[str] = Query(None, description="自定义搜索关键字"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    从PT站点手动同步该订阅的资源（异步后台任务）
    
    - **subscription_id**: 订阅ID
    - **site_id**: 可选，指定PT站点ID
    - **keyword**: 可选，自定义搜索关键字（默认使用订阅标题）
    
    返回任务执行ID
    """
    import asyncio
    from app.constants import TASK_TYPE_PT_RESOURCE_SYNC
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.task_execution_service import TaskExecutionService

    # 获取订阅
    subscription = await SubscriptionService.get_by_id(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订阅ID {subscription_id} 不存在",
        )

    # 检查权限
    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订阅",
        )

    # 确定搜索关键字
    search_keyword = keyword if keyword else subscription.title

    # 确定站点
    if site_id:
        from app.models.pt_site import PTSite
        site = await db.get(PTSite, site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"站点ID {site_id} 不存在")
        site_name = site.name
        sites = [site]
    else:
        # 获取所有启用的站点
        from app.models.pt_site import PTSite
        from sqlalchemy import select
        query = select(PTSite).where(PTSite.status == "active", PTSite.sync_enabled == True)
        result = await db.execute(query)
        sites = result.scalars().all()
        if not sites:
            raise HTTPException(status_code=400, detail="没有可用的PT站点")
        site_name = "所有启用站点"

    # 创建任务
    execution_ids = []
    messages = []
    
    for site in sites:
        task_name = f"同步资源: {search_keyword} ({site.name})"
        
        # 准备参数
        handler_params = {
            "site_id": site.id,
            "sync_type": "manual",
            "max_pages": 3,
            "keyword": search_keyword,
            # 对于电视剧订阅，通常我们只搜索标题，后续匹配由订阅规则处理
            # 这里不强制 mode，让 PT 站点搜索尽可能多的相关结果
            "mode": "normal", 
        }

        execution_data = TaskExecutionCreate(
            task_type=TASK_TYPE_PT_RESOURCE_SYNC,
            task_name=task_name,
            handler=TASK_TYPE_PT_RESOURCE_SYNC,
            handler_params=handler_params
        )
        
        execution = await TaskExecutionService.create(db, execution_data)
        execution_ids.append(execution.id)

        # 后台执行
        from app.services.task.scheduler_manager import scheduler_manager
        asyncio.create_task(
            scheduler_manager._execute_task_by_execution(execution.id)
        )
    
    return {
        "execution_ids": execution_ids,
        "subscription_id": subscription_id,
        "keyword": search_keyword,
        "sites_count": len(sites),
        "message": f"已创建 {len(sites)} 个同步任务，正在搜索 '{search_keyword}'"
    }
