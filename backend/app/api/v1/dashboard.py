# -*- coding: utf-8 -*-
"""
仪表盘API
"""
import datetime as _dt
import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.utils.timezone import now as tz_now, ensure_timezone, get_system_timezone
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.media_server_config import MediaServerConfig
from app.models.pt_site import PTSite
from app.models.pt_resource import PTResource
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_person import UnifiedPerson
from app.models.subscription import Subscription
from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.image_cache import ImageCache
from app.models.task_execution import TaskExecution
from app.schemas.dashboard import (
    DashboardStatsResponse,
    DashboardActivityResponse,
    DashboardBackdropsResponse,
    DashboardWatchHistoryResponse,
    MediaBackdropItem,
)
from app.schemas.task_execution import TaskExecutionSummary
from app.services.common.system_setting_service import SystemSettingService

logger = logging.getLogger(__name__)
router = APIRouter()

# 用于 updated_at 为 None 时的兜底排序值（使用系统时区）
_EPOCH = _dt.datetime(2000, 1, 1, tzinfo=get_system_timezone())

# stats 接口短时缓存（系统级数据，60s 内不需要实时精确）
_stats_cache: dict[str, tuple[float, "DashboardStatsResponse"]] = {}
_STATS_TTL = 60.0


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取仪表盘统计指标（纯 DB count 查询，快速返回）。
    观看历史请使用 /dashboard/watch-history 懒加载。
    近期活动请使用 /dashboard/activity 懒加载。
    """
    # 命中缓存直接返回（60s TTL）
    _now = time.monotonic()
    cached = _stats_cache.get("stats")
    if cached and _now - cached[0] < _STATS_TTL:
        return cached[1]

    t_start = time.perf_counter()
    today_start = tz_now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ── 所有计数：单次 SQL 批量查询（减少 DB 往返从 18+ 次到 1 次）──────
    _c = (await db.execute(select(
        select(func.count(PTSite.id)).scalar_subquery().label("total_sites"),
        select(func.count(PTResource.id)).scalar_subquery().label("total_resources"),
        select(func.count(UnifiedMovie.id)).scalar_subquery().label("total_movies"),
        select(func.count(UnifiedTVSeries.id)).scalar_subquery().label("total_tvs"),
        select(func.count(UnifiedPerson.id)).scalar_subquery().label("total_actors"),
        select(func.count(PTResource.id)).where(
            PTResource.created_at >= today_start
        ).scalar_subquery().label("today_new_resources"),
        select(func.count(UnifiedMovie.id)).where(
            UnifiedMovie.created_at >= today_start
        ).scalar_subquery().label("today_new_movies"),
        select(func.count(UnifiedTVSeries.id)).where(
            UnifiedTVSeries.created_at >= today_start
        ).scalar_subquery().label("today_new_tvs"),
        select(func.count(UnifiedTVSeries.id)).where(
            UnifiedTVSeries.updated_at >= today_start,
            UnifiedTVSeries.created_at < today_start,
        ).scalar_subquery().label("today_updated_tvs"),
        select(func.count(UnifiedPerson.id)).where(
            UnifiedPerson.created_at >= today_start
        ).scalar_subquery().label("today_new_actors"),
        select(func.count(Subscription.id)).scalar_subquery().label("total_subscriptions"),
        select(func.count(Subscription.id)).where(
            Subscription.created_at >= today_start
        ).scalar_subquery().label("today_new_subscriptions"),
        select(func.count(DownloadTask.id)).scalar_subquery().label("total_downloads"),
        select(func.count(DownloadTask.id)).where(
            DownloadTask.status == "downloading"
        ).scalar_subquery().label("active_downloads"),
        select(func.count(DownloadTask.id)).where(
            DownloadTask.created_at >= today_start
        ).scalar_subquery().label("today_new_downloads"),
        select(func.coalesce(func.sum(MediaFile.file_size), 0)).scalar_subquery().label("total_storage_used"),
        select(func.count(MediaServerConfig.id)).scalar_subquery().label("media_server_count"),
        select(func.count(ImageCache.id)).scalar_subquery().label("image_cache_count"),
        select(func.coalesce(func.sum(ImageCache.size_bytes), 0)).scalar_subquery().label("image_cache_size"),
    ))).one()
    t_counts = time.perf_counter()
    logger.debug(f"[dashboard/stats] counts_query={t_counts - t_start:.3f}s")

    # ── 媒体服务器媒体总量（逐个服务器读取 DB 缓存）────────────────────
    from app.services.media_server.media_server_library_service import MediaServerLibraryService
    total_media_items = 0
    configs_res = await db.execute(select(MediaServerConfig.id))
    for cfg_id in configs_res.scalars():
        try:
            s = await MediaServerLibraryService.get_library_stats(db, cfg_id)
            total_media_items += s.get("movie_count", 0) + s.get("episode_count", 0)
        except Exception:
            pass
    t_media = time.perf_counter()
    logger.debug(f"[dashboard/stats] media_items={t_media - t_counts:.3f}s total={total_media_items}")
    logger.debug(f"[dashboard/stats] total={t_media - t_start:.3f}s")

    result = DashboardStatsResponse(
        # 发现
        total_sites=_c.total_sites or 0,
        total_resources=_c.total_resources or 0,
        total_movies=_c.total_movies or 0,
        total_tvs=_c.total_tvs or 0,
        total_actors=_c.total_actors or 0,
        today_new_resources=_c.today_new_resources or 0,
        today_new_movies=_c.today_new_movies or 0,
        today_new_tvs=_c.today_new_tvs or 0,
        today_updated_tvs=_c.today_updated_tvs or 0,
        today_new_actors=_c.today_new_actors or 0,
        # 媒体
        total_subscriptions=_c.total_subscriptions or 0,
        today_new_subscriptions=_c.today_new_subscriptions or 0,
        total_downloads=_c.total_downloads or 0,
        active_downloads=_c.active_downloads or 0,
        today_new_downloads=_c.today_new_downloads or 0,
        total_storage_used=int(_c.total_storage_used or 0),
        media_server_count=_c.media_server_count or 0,
        total_media_items=total_media_items,
        # 系统
        image_cache_count=_c.image_cache_count or 0,
        image_cache_size=int(_c.image_cache_size or 0),
        # 以下字段改用独立懒加载接口
        recent_watch_history=[],
        recent_media_backdrops=[],
        recent_activities=[],
    )
    _stats_cache["stats"] = (time.monotonic(), result)
    return result


@router.get("/backdrops", response_model=DashboardBackdropsResponse)
async def get_dashboard_backdrops(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取 Hero 轮播背景图（独立懒加载，纯 DB 查询，应最快返回）。
    前端可与 /dashboard/stats 并行发起，优先渲染 Hero 区域图片。
    """
    t_start = time.perf_counter()

    # 从系统设置读取背景图数量，默认 10
    _count_setting = await SystemSettingService.get_by_key(db, "homepage", "backdrop_count")
    try:
        backdrop_count = int(_count_setting.value) if _count_setting else 10
        backdrop_count = max(1, min(backdrop_count, 50))
    except (ValueError, TypeError):
        backdrop_count = 10

    movie_rows = (await db.execute(
        select(
            UnifiedMovie.id, UnifiedMovie.title, UnifiedMovie.year,
            UnifiedMovie.backdrop_url, UnifiedMovie.poster_url,
            UnifiedMovie.rating_tmdb, UnifiedMovie.updated_at,
            UnifiedMovie.overview,
        )
        .where(UnifiedMovie.backdrop_url.is_not(None))
        .order_by(desc(UnifiedMovie.updated_at))
        .limit(backdrop_count)
    )).all()

    tv_rows = (await db.execute(
        select(
            UnifiedTVSeries.id, UnifiedTVSeries.title, UnifiedTVSeries.year,
            UnifiedTVSeries.backdrop_url, UnifiedTVSeries.poster_url,
            UnifiedTVSeries.rating_tmdb, UnifiedTVSeries.updated_at,
            UnifiedTVSeries.overview,
        )
        .where(UnifiedTVSeries.backdrop_url.is_not(None))
        .order_by(desc(UnifiedTVSeries.updated_at))
        .limit(backdrop_count)
    )).all()

    combined: list[tuple] = []
    for row in movie_rows:
        combined.append((ensure_timezone(row.updated_at) if row.updated_at else _EPOCH, "movie", row))
    for row in tv_rows:
        combined.append((ensure_timezone(row.updated_at) if row.updated_at else _EPOCH, "tv", row))
    combined.sort(key=lambda x: x[0], reverse=True)

    backdrops = [
        MediaBackdropItem(
            id=row.id,
            media_type=mtype,
            title=row.title,
            year=row.year,
            backdrop_url=row.backdrop_url,
            poster_url=row.poster_url,
            rating=float(row.rating_tmdb) if row.rating_tmdb else None,
            overview=row.overview,
        )
        for _, mtype, row in combined[:backdrop_count]
    ]
    logger.debug(
        f"[dashboard/backdrops] total={time.perf_counter() - t_start:.3f}s count={len(backdrops)}"
    )
    return DashboardBackdropsResponse(recent_media_backdrops=backdrops)


@router.get("/watch-history", response_model=DashboardWatchHistoryResponse)
async def get_dashboard_watch_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取最近观看历史（独立懒加载，避免阻塞首屏统计数据）。
    此接口会调用媒体服务器 API，响应较慢。
    """
    t_start = time.perf_counter()
    from app.services.media_server.media_server_watch_history_service import MediaServerWatchHistoryService
    history_items, _ = await MediaServerWatchHistoryService.get_user_watch_history(
        db, current_user.id, limit=8
    )
    logger.debug(
        f"[dashboard/watch-history] total={time.perf_counter() - t_start:.3f}s count={len(history_items)}"
    )
    return DashboardWatchHistoryResponse(watch_history=history_items)


@router.get("/activity", response_model=DashboardActivityResponse)
async def get_dashboard_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取近期任务活动（独立懒加载，避免阻塞首屏统计数据）
    """
    t_start = time.perf_counter()
    result = await db.execute(
        select(TaskExecution)
        .order_by(desc(TaskExecution.updated_at))
        .limit(10)
    )
    recent_tasks = result.scalars().all()
    logger.debug(
        f"[dashboard/activity] total={time.perf_counter() - t_start:.3f}s count={len(recent_tasks)}"
    )

    return DashboardActivityResponse(
        recent_activities=[
            TaskExecutionSummary(
                id=task.id,
                task_name=task.task_name,
                task_type=task.task_type,
                status=task.status,
                progress=task.progress,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                duration=task.duration,
                handler_params=task.handler_params,
                error_message=task.error_message,
            )
            for task in recent_tasks
        ]
    )
