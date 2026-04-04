# -*- coding: utf-8 -*-
"""
媒体服务器 API 路由（通用：Jellyfin/Emby/Plex）
"""
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import httpx
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.media_server_item import MediaServerItem
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.media_server.media_server_watch_history_service import MediaServerWatchHistoryService
from app.services.media_server.media_server_library_service import MediaServerLibraryService
from app.services.task.task_execution_service import TaskExecutionService
from app.schemas.media_server import (
    MediaServerConfigCreate,
    MediaServerConfigUpdate,
    MediaServerConfigResponse,
    MediaServerTestConnectionResponse,
    MediaServerRefreshLibraryResponse,
    MediaServerSyncHistoryResponse,
    MediaServerLibraryResponse,
    MediaServerStatsResponse,
    MediaServerWatchHistoryResponse,
    MediaServerWatchHistoryListResponse,
    MediaServerWatchStatisticsResponse,
)
from app.schemas.task_execution import TaskExecutionCreate
from app.constants.task import (
    TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH,
    TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
)
from app.services.task.scheduler_manager import scheduler_manager
from app.services.media_server.media_server_item_service import MediaServerItemService
from app.schemas.media_server import (
    MediaServerItemListResponse,
    MediaServerItemResponse,
    MediaServerItemSyncResponse,
)

router = APIRouter(prefix="/media-servers", tags=["Media Servers"])


# ============================================================================
# 配置管理
# ============================================================================


@router.get("/configs", response_model=List[MediaServerConfigResponse])
async def get_media_server_configs(
    server_type: Optional[str] = Query(None, description="服务器类型过滤：jellyfin/emby/plex"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取媒体服务器配置列表

    可选参数：
    - server_type: 按服务器类型过滤
    """
    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    configs = await MediaServerConfigService.get_by_user_id(
        db, current_user.id, server_type
    )

    # 为每个配置添加认证信息已设置标志
    items = []
    for config in configs:
        # 获取模型的所有列
        config_data = {c.key: getattr(config, c.key) for c in sqlalchemy_inspect(config).mapper.column_attrs}
        # 添加认证标志
        config_data['has_api_key'] = bool(config.api_key)
        config_data['has_token'] = bool(config.token)
        config_data['has_password'] = bool(config.password)
        items.append(config_data)

    return items


@router.post("/configs", response_model=MediaServerConfigResponse)
async def create_media_server_config(
    config_data: MediaServerConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建媒体服务器配置

    根据 type 字段选择服务器类型：
    - jellyfin: 需要 api_key
    - emby: 需要 api_key
    - plex: 需要 token
    """
    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    config = await MediaServerConfigService.create(db, current_user.id, config_data.dict())

    # 添加认证信息已设置标志
    config_data_dict = {c.key: getattr(config, c.key) for c in sqlalchemy_inspect(config).mapper.column_attrs}
    config_data_dict['has_api_key'] = bool(config.api_key)
    config_data_dict['has_token'] = bool(config.token)
    config_data_dict['has_password'] = bool(config.password)

    return config_data_dict


@router.get("/configs/{config_id}", response_model=MediaServerConfigResponse)
async def get_media_server_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取配置详情"""
    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")

    # 权限检查
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 添加认证信息已设置标志
    config_data = {c.key: getattr(config, c.key) for c in sqlalchemy_inspect(config).mapper.column_attrs}
    config_data['has_api_key'] = bool(config.api_key)
    config_data['has_token'] = bool(config.token)
    config_data['has_password'] = bool(config.password)

    return config_data


@router.put("/configs/{config_id}", response_model=MediaServerConfigResponse)
async def update_media_server_config(
    config_id: int,
    updates: MediaServerConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新配置

    只更新提供的字段
    """
    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 执行更新
    updated_config = await MediaServerConfigService.update(
        db, config_id, updates.dict(exclude_unset=True)
    )

    # 添加认证信息已设置标志
    config_data_dict = {c.key: getattr(updated_config, c.key) for c in sqlalchemy_inspect(updated_config).mapper.column_attrs}
    config_data_dict['has_api_key'] = bool(updated_config.api_key)
    config_data_dict['has_token'] = bool(updated_config.token)
    config_data_dict['has_password'] = bool(updated_config.password)

    return config_data_dict


@router.delete("/configs/{config_id}")
async def delete_media_server_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除配置"""
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 执行删除
    await MediaServerConfigService.delete(db, config_id)
    return {"message": "配置已删除"}


@router.post("/configs/{config_id}/test", response_model=MediaServerTestConnectionResponse)
async def test_media_server_connection(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    测试连接

    验证服务器地址、端口和认证信息是否正确
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 测试连接
    success, message = await MediaServerConfigService.test_connection(db, config_id)
    return MediaServerTestConnectionResponse(success=success, message=message)


# ============================================================================
# 媒体库管理
# ============================================================================


@router.get("/{config_id}/libraries", response_model=List[MediaServerLibraryResponse])
async def get_media_server_libraries(
    config_id: int,
    include_hidden: bool = Query(False, description="是否包含隐藏的媒体库"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取媒体库列表

    返回服务器上所有媒体库（电影、剧集等）
    
    参数：
    - include_hidden: 是否包含隐藏的媒体库
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 获取媒体库
    libraries = await MediaServerLibraryService.get_libraries(db, config_id, include_hidden=include_hidden)
    return libraries


@router.post("/{config_id}/libraries/refresh", response_model=MediaServerRefreshLibraryResponse)
async def refresh_media_server_library(
    config_id: int,
    library_id: Optional[str] = Query(None, description="媒体库ID，不提供则刷新所有"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刷新媒体库

    参数：
    - library_id: 可选，指定媒体库ID，不提供则全局刷新
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 刷新媒体库
    success = await MediaServerLibraryService.refresh_library(db, config_id, library_id)

    if success:
        message = f"媒体库刷新请求已发送"
        if library_id:
            message += f"（媒体库 ID: {library_id}）"
    else:
        message = "媒体库刷新失败"

    return MediaServerRefreshLibraryResponse(success=success, message=message)


@router.get("/{config_id}/stats", response_model=MediaServerStatsResponse)
async def get_media_server_stats(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取统计信息

    返回媒体库的统计数据（电影数量、剧集数量等）
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 获取统计
    stats = await MediaServerLibraryService.get_library_stats(db, config_id)
    return MediaServerStatsResponse(**stats)


@router.get("/{config_id}/sessions")
async def get_media_server_sessions(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取活动会话
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        adapter = MediaServerConfigService.get_adapter(config)
        sessions = await adapter.get_sessions()
        # 注入 config_id 以便前端生成图片链接
        for session in sessions:
            session['config_id'] = config_id
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_id}/latest")
async def get_media_server_latest(
    config_id: int,
    limit: int = 20,
    item_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    从本地缓存获取最近添加的媒体（快速，无需实时请求媒体服务器）
    item_type: 可选过滤，如 Movie / Episode
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    query = (
        select(MediaServerItem)
        .where(
            MediaServerItem.media_server_config_id == config_id,
            MediaServerItem.is_active == True,
        )
    )
    if item_type:
        query = query.where(MediaServerItem.item_type == item_type)

    # 应用媒体库显示设置过滤
    excluded_ids = await MediaServerConfigService.get_excluded_library_ids(db, config_id)
    if excluded_ids:
        query = query.where(or_(
            MediaServerItem.library_id == None,
            MediaServerItem.library_id.not_in(excluded_ids)
        ))

    result = await db.execute(
        query.order_by(desc(MediaServerItem.date_created)).limit(limit)
    )
    items = result.scalars().all()

    return [
        {
            "Id": item.server_item_id,
            "Name": item.name,
            "Type": item.item_type,
            "DateCreated": item.date_created.isoformat() if item.date_created else None,
            "ProductionYear": item.year,
            "SeriesName": item.series_name,
            "ParentIndexNumber": item.season_number,
            "IndexNumber": item.episode_number,
            "config_id": config_id,
        }
        for item in items
    ]


from app.services.common.image_cache_service import ImageCacheService
from fastapi.responses import FileResponse

@router.get("/{config_id}/image")
async def get_media_server_image(
    config_id: int,
    path: str = Query(..., description="图片相对路径，例如 /Items/{Id}/Images/Primary"),
    db: AsyncSession = Depends(get_db),
    # 移除 current_user 依赖，允许 <img> 标签直接访问
    # current_user: User = Depends(get_current_user),
):
    """
    代理获取媒体服务器图片 (带缓存)
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    
    # 注意：由于移除了用户认证，此处不再校验 config.user_id
    # 这是一个权衡，为了让前端图片能正常加载。
    # 风险：任何人知道 config_id 和 path 都能查看图片。
    
    try:
        adapter = MediaServerConfigService.get_adapter(config)
        
        # 构造完整URL并附加认证参数，以便 ImageCacheService 可以直接下载
        url = f"{adapter.base_url}{path}"
        
        separator = "&" if "?" in url else "?"
        
        if hasattr(adapter, 'api_key') and adapter.api_key:
             # Jellyfin/Emby
             url = f"{url}{separator}api_key={adapter.api_key}"
             separator = "&" # 后续参数用 &
             
        if hasattr(adapter, 'token') and adapter.token:
             # Plex
             url = f"{url}{separator}X-Plex-Token={adapter.token}"

        # 使用图片缓存服务
        cache = await ImageCacheService.download_and_cache(db, url)

        if not cache:
            raise HTTPException(status_code=502, detail="Failed to fetch image")

        file_path = ImageCacheService.get_file_path(cache)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Cache file missing")

        return FileResponse(
            path=str(file_path),
            media_type=cache.content_type,
            headers={
                "Cache-Control": "public, max-age=31536000",
                "X-Cache-Hit": "true",
            },
        )

    except Exception as e:
        # Log error in production
        # print(f"Image proxy error: {e}")
        raise HTTPException(status_code=404, detail="Image not found")


@router.get("/{config_id}/items/{item_id}")
async def get_media_server_item(
    config_id: int,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取项目详情
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        adapter = MediaServerConfigService.get_adapter(config)
        item = await adapter.get_item(item_id)
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_id}/search")
async def search_media_server(
    config_id: int,
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    搜索媒体
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        adapter = MediaServerConfigService.get_adapter(config)
        results = await adapter.search(query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# 观看历史
# ============================================================================


@router.get("/history", response_model=MediaServerWatchHistoryListResponse)
async def get_watch_history(
    config_id: Optional[int] = Query(None, description="媒体服务器配置ID过滤"),
    media_type: Optional[str] = Query(None, description="媒体类型过滤：movie/tv/music"),
    is_completed: Optional[bool] = Query(None, description="是否看完过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取观看历史

    支持过滤：
    - config_id: 按媒体服务器配置过滤
    - media_type: 按媒体类型过滤
    - is_completed: 按完成状态过滤
    - 分页参数
    """
    # 处理媒体类型别名
    if media_type == "episode":
        media_type = "tv"

    filters = {
        "config_id": config_id,
        "media_type": media_type,
        "is_completed": is_completed,
        "page": page,
        "page_size": page_size,
    }

    limit = page_size
    offset = (page - 1) * page_size

    history, total = await MediaServerWatchHistoryService.get_user_watch_history(
        db, current_user.id, filters, limit=limit, offset=offset
    )

    return MediaServerWatchHistoryListResponse(
        items=history, total=total, page=page, page_size=page_size
    )


@router.get("/history/statistics", response_model=MediaServerWatchStatisticsResponse)
async def get_watch_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取观看统计

    返回用户的观看统计数据（总数、完成数、按类型统计等）
    """
    stats = await MediaServerWatchHistoryService.get_watch_statistics(db, current_user.id)
    return stats


@router.post("/{config_id}/history/sync", response_model=MediaServerSyncHistoryResponse)
async def sync_watch_history(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动同步观看历史

    从媒体服务器拉取最新的观看历史数据
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 执行同步
    result = await MediaServerWatchHistoryService.sync_watch_history(db, config_id)

    return MediaServerSyncHistoryResponse(
        synced_count=result.get("synced_count", 0),
        new_count=result.get("new_count", 0),
        updated_count=result.get("updated_count", 0),
    )


@router.post("/{config_id}/history/rematch")
async def batch_rematch_watch_history(
    config_id: int,
    unmatched_only: bool = Query(False, description="是否只匹配未关联的记录"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量重新匹配观看历史到本地资源

    使用增强的匹配逻辑重新匹配观看历史：
    - Provider IDs 优先（TMDb/IMDb/豆瓣）
    - 文件路径映射匹配
    - 标题+年份精确/模糊匹配

    参数：
    - unmatched_only: 仅处理未匹配的记录（默认 False）

    返回任务执行 ID，可通过任务系统查询进度
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 创建任务执行记录
    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH,
        task_name=f"批量重新匹配观看历史 - {config.name}",
        handler=TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH,
        handler_params={
            "config_id": config_id,
            "user_id": current_user.id,
            "unmatched_only": unmatched_only,
        },
    )
    execution = await TaskExecutionService.create(db, execution_data)

    # 后台执行任务（不阻塞 API 响应）
    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return {
        "execution_id": execution.id,
        "message": "批量匹配任务已创建，请查询任务执行状态获取进度",
    }


# ============================================================================
# 媒体库媒体项管理（本地缓存）
# ============================================================================


@router.get("/{config_id}/library-items", response_model=MediaServerItemListResponse)
async def get_media_server_library_items(
    config_id: int,
    media_type: Optional[str] = Query(None, description="媒体类型过滤：movie/tv/music/book/anime/adult/game/other"),
    item_type: Optional[str] = Query(None, description="媒体项类型过滤（单个）：Movie/Episode/Series/Season"),
    item_types: Optional[str] = Query(None, description="媒体项类型过滤（多个，逗号分隔）：Movie,Series"),
    library_id: Optional[str] = Query(None, description="媒体库ID过滤"),
    has_media_file: Optional[bool] = Query(None, description="是否已关联本地文件"),
    has_unified_resource: Optional[bool] = Query(None, description="是否已关联统一资源"),
    keyword: Optional[str] = Query(None, description="关键词搜索（标题）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    order_by: str = Query("synced_at", description="排序字段"),
    order_desc: bool = Query(True, description="是否降序"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取媒体库媒体项列表（从本地数据库查询，性能优化）

    此接口从本地缓存的 media_server_items 表查询，避免每次都请求 Jellyfin API。

    支持筛选：
    - media_type: 按媒体类型过滤
    - item_type: 按媒体项类型过滤（单个）
    - item_types: 按媒体项类型过滤（多个，逗号分隔，如 "Movie,Series"）
    - library_id: 按媒体库过滤
    - has_media_file: 是否已关联本地文件
    - has_unified_resource: 是否已关联统一资源
    - keyword: 标题关键词搜索
    - 分页和排序
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 应用媒体库显示设置过滤
    excluded_ids = await MediaServerConfigService.get_excluded_library_ids(db, config_id) or None

    # 解析 item_types 参数
    item_types_list = None
    if item_types:
        item_types_list = [t.strip() for t in item_types.split(",") if t.strip()]

    # 查询媒体项
    items, total = await MediaServerItemService.get_list(
        db=db,
        config_id=config_id,
        media_type=media_type,
        item_type=item_type,
        item_types=item_types_list,
        library_id=library_id,
        is_active=True,
        has_media_file=has_media_file,
        has_unified_resource=has_unified_resource,
        keyword=keyword,
        excluded_library_ids=excluded_ids,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_desc=order_desc,
    )

    # 转换为响应格式（添加额外字段）
    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    # 批量获取 Series 的季/集统计
    series_server_ids = [item.server_item_id for item in items if item.item_type == "Series"]
    series_stats = {}
    if series_server_ids:
        series_stats = await MediaServerItemService.get_series_stats(db, config_id, series_server_ids)

    response_items = []
    for item in items:
        item_data = {c.key: getattr(item, c.key) for c in sqlalchemy_inspect(item).mapper.column_attrs}

        # 规范化 studios、genres、tags 字段（确保为字符串列表）
        for field in ["studios", "genres", "tags"]:
            if item_data.get(field) and isinstance(item_data[field], list):
                item_data[field] = [
                    x.get("Name", "") if isinstance(x, dict) else str(x)
                    for x in item_data[field]
                ]

        # 添加前端需要的额外字段
        item_data["server_name"] = config.name

        # 构建 Web URL（Jellyfin）
        if config.type == "jellyfin":
            protocol = "https" if config.use_ssl else "http"
            base_url = f"{protocol}://{config.host}:{config.port}"
            item_data["web_url"] = f"{base_url}/web/index.html#!/details?id={item.server_item_id}"

        # 构建图片 URL（使用代理接口）
        if item.images and item.images.get("Primary"):
            item_data["image_url"] = f"/api/v1/media-servers/{config_id}/image?path={item.images['Primary']}"

        # 为 Series 类型添加季/集统计
        if item.item_type == "Series" and item.server_item_id in series_stats:
            stats = series_stats[item.server_item_id]
            item_data["season_count"] = stats["season_count"]
            item_data["episode_count"] = stats["episode_count"]

        response_items.append(item_data)

    return MediaServerItemListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{config_id}/library-items/sync")
async def sync_media_server_library(
    config_id: int,
    library_ids: Optional[List[str]] = Query(None, description="要同步的媒体库ID列表（可选）"),
    match_files: bool = Query(True, description="是否自动匹配本地文件"),
    sync_mode: str = Query("full", description="同步模式：full（全量）或 incremental（增量）"),
    incremental_hours: int = Query(24, description="增量同步时间范围（小时），默认24小时", ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    触发媒体库同步任务

    从媒体服务器同步媒体项到本地数据库。

    参数：
    - library_ids: 指定要同步的媒体库ID（不传则同步所有）
    - match_files: 是否自动匹配本地媒体文件（默认 True）
    - sync_mode: 同步模式
        - full: 全量同步（扫描所有媒体项）
        - incremental: 增量同步（仅同步最近修改的项）
    - incremental_hours: 增量同步时间范围（小时），默认24小时，范围1-168小时（7天）

    返回任务执行 ID，可通过任务系统查询进度。
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 创建任务执行记录
    sync_mode_text = "增量同步" if sync_mode == "incremental" else "全量同步"
    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
        task_name=f"{sync_mode_text} - {config.name}",
        handler=TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
        handler_params={
            "media_server_config_id": config_id,
            "library_ids": library_ids,
            "match_files": match_files,
            "sync_mode": sync_mode,
            "incremental_hours": incremental_hours,
        },
    )
    execution = await TaskExecutionService.create(db, execution_data)

    # 后台执行任务（不阻塞 API 响应）
    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return {
        "execution_id": execution.id,
        "message": "媒体库同步任务已创建，请查询任务执行状态获取进度",
    }


@router.get("/{config_id}/library-items/statistics")
async def get_media_server_library_statistics(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取媒体库统计信息

    返回媒体项数量统计、类型分布、匹配情况等。
    """
    # 权限检查
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 获取统计信息
    stats = await MediaServerItemService.get_statistics(db, config_id)

    return stats


@router.get("/{config_id}/library-items/series/{series_id}/seasons")
async def get_series_seasons(
    config_id: int,
    series_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取剧集的所有季，包含每季的集数统计

    返回结构：
    {
        "series": {...},       // 剧集信息
        "seasons": [           // 季列表
            {
                "season_number": 1,
                "season_name": "第 1 季",
                "season_id": "xxx",
                "episode_count": 12,
                "image_url": "...",
            }
        ]
    }
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    data = await MediaServerItemService.get_series_children(db, config_id, series_id)

    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    # 转换 series 信息
    series_data = None
    if data["series"]:
        series_item = data["series"]
        series_data = {c.key: getattr(series_item, c.key) for c in sqlalchemy_inspect(series_item).mapper.column_attrs}
        series_data["server_name"] = config.name
        if series_item.images and series_item.images.get("Primary"):
            series_data["image_url"] = f"/api/v1/media-servers/{config_id}/image?path={series_item.images['Primary']}"
        if config.type == "jellyfin":
            protocol = "https" if config.use_ssl else "http"
            base_url = f"{protocol}://{config.host}:{config.port}"
            series_data["web_url"] = f"{base_url}/web/index.html#!/details?id={series_item.server_item_id}"

    # 转换 seasons 信息
    seasons_response = []
    for season in data["seasons"]:
        season_resp = {
            "season_number": season["season_number"],
            "season_name": season["season_name"],
            "season_id": season["season_id"],
            "episode_count": len(season["episodes"]),
            "image_url": None,
        }
        # 尝试从 Season 对象获取图片，如果没有则从第一集获取
        if season["season_id"]:
            # 查找 Season 类型的条目获取图片
            for child in data["seasons"]:
                if child["season_id"] == season["season_id"]:
                    break
        # 用第一集的图片作为备选
        if season["episodes"]:
            first_ep = season["episodes"][0]
            if first_ep.images and first_ep.images.get("Primary"):
                season_resp["image_url"] = f"/api/v1/media-servers/{config_id}/image?path={first_ep.images['Primary']}"

        seasons_response.append(season_resp)

    return {
        "series": series_data,
        "seasons": seasons_response,
    }


@router.get("/{config_id}/library-items/series/{series_id}/seasons/{season_number}/episodes")
async def get_season_episodes(
    config_id: int,
    series_id: str,
    season_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取某一季的所有集

    返回结构：
    {
        "season": {...},       // 季信息（可能为 null）
        "episodes": [...]      // 集列表
    }
    """
    config = await MediaServerConfigService.get_by_id(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Media server config not found")
    if config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    season_item, episodes = await MediaServerItemService.get_season_episodes(
        db, config_id, series_id, season_number
    )

    from sqlalchemy.inspection import inspect as sqlalchemy_inspect

    def build_item_data(item):
        item_data = {c.key: getattr(item, c.key) for c in sqlalchemy_inspect(item).mapper.column_attrs}
        item_data["server_name"] = config.name
        if config.type == "jellyfin":
            protocol = "https" if config.use_ssl else "http"
            base_url = f"{protocol}://{config.host}:{config.port}"
            item_data["web_url"] = f"{base_url}/web/index.html#!/details?id={item.server_item_id}"
        if item.images and item.images.get("Primary"):
            item_data["image_url"] = f"/api/v1/media-servers/{config_id}/image?path={item.images['Primary']}"
        return item_data

    season_data = build_item_data(season_item) if season_item else None
    episodes_data = [build_item_data(ep) for ep in episodes]

    return {
        "season": season_data,
        "episodes": episodes_data,
    }
