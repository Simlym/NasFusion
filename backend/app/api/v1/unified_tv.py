# -*- coding: utf-8 -*-
"""
统一电视剧资源API接口
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.unified_tv import UnifiedTVResponse, UnifiedTVWithPTResources, UnifiedTVListResponse, UnifiedTVUpdate
from app.services.identification.unified_tv_series_service import UnifiedTVSeriesService
from app.services.identification.metadata_refresh_service import MetadataRefreshService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unified/tv", tags=["统一电视剧资源"])


@router.get("", response_model=dict)
async def get_tv_series(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    has_free_resource: Optional[bool] = Query(None, description="是否有免费资源"),
    year: Optional[int] = Query(None, description="年份"),
    genre: Optional[str] = Query(None, description="类型"),
    country: Optional[str] = Query(None, description="国家/地区"),
    status: Optional[str] = Query(None, description="状态（Returning Series/Ended/Canceled）"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段: created_at, rating, year, title"),
    order: str = Query("desc", description="排序方向: asc, desc"),
    min_rating: Optional[float] = Query(None, description="最低评分"),
    trending_collection: Optional[str] = Query(None, description="榜单类型（如: douban_weekly_best）"),
    exclude_genre: Optional[str] = Query(None, description="排除的类型（如'动画'）"),
    has_local: Optional[bool] = Query(None, description="是否有本地文件"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取统一电视剧资源列表

    支持筛选和搜索：
    - **has_free_resource**: 是否有免费PT资源
    - **year**: 年份
    - **genre**: 类型（如"剧情"、"喜剧"）
    - **country**: 国家/地区
    - **status**: 状态（Returning Series/Ended/Canceled/In Production）
    - **search**: 标题搜索
    - **sort_by**: 排序字段
    - **order**: 排序方向
    - **min_rating**: 最低评分
    - **trending_collection**: 榜单类型（用于筛选和排序）
    - **exclude_genre**: 排除的类型
    - **has_local**: 是否有本地文件

    返回分页结果
    """
    skip = (page - 1) * page_size

    tv_series, total = await UnifiedTVSeriesService.get_list(
        db=db,
        skip=skip,
        limit=page_size,
        has_free_resource=has_free_resource,
        year=year,
        genre=genre,
        country=country,
        status=status,
        search=search,
        sort_by=sort_by,
        order=order,
        min_rating=min_rating,
        trending_collection=trending_collection,
        exclude_genre=exclude_genre,
        has_local=has_local,
    )

    return {
        "items": [UnifiedTVListResponse.model_validate(tv).model_dump(by_alias=True) for tv in tv_series],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{tv_id}")
async def get_tv_detail(
    tv_id: int,
    pt_page: int = Query(1, ge=1, description="PT资源页码"),
    pt_page_size: int = Query(20, ge=1, le=100, description="PT资源每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取统一电视剧资源详情（含关联的PT资源列表，支持分页）

    - **tv_id**: 电视剧ID
    - **pt_page**: PT资源页码（默认1）
    - **pt_page_size**: PT资源每页数量（默认20，最大100）

    返回电视剧详情和关联的PT资源列表（分页）
    """
    tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
    if not tv:
        raise HTTPException(status_code=404, detail="电视剧不存在")

    # 构建响应数据（使用 camelCase）
    tv_data = UnifiedTVResponse.model_validate(tv).model_dump(by_alias=True)

    # 获取关联的PT资源（分页）
    from app.models.resource_mapping import ResourceMapping
    from app.models.pt_resource import PTResource
    from app.models.download_task import DownloadTask
    from app.models.unified_person import TVSeriesCredit
    from app.schemas.pt_resource import PTResourceResponse
    from sqlalchemy import select, func
    from sqlalchemy.orm import joinedload, selectinload

    # --- 从关系表加载演职员信息，确保使用本地 Person ID ---
    try:
        credits_query = (
            select(TVSeriesCredit)
            .options(selectinload(TVSeriesCredit.person))
            .where(TVSeriesCredit.tv_series_id == tv_id)
            .order_by(TVSeriesCredit.order.asc())
        )
        credits_result = await db.execute(credits_query)
        credits_list = credits_result.scalars().all()

        real_creators = []
        real_directors = []
        real_actors = []

        for credit in credits_list:
            if not credit.person:
                continue

            person_data = {
                "id": credit.person.id,
                "name": credit.person.name,
                "douban_id": credit.person.douban_id,
                "imdb_id": credit.person.imdb_id,
                "tmdb_id": credit.person.tmdb_id,
                "thumb_url": credit.person.profile_url,
            }

            if credit.job == "Creator":
                real_creators.append(person_data)
            elif credit.job == "Director":
                real_directors.append(person_data)
            elif credit.job == "Actor":
                person_data["character"] = credit.character
                person_data["order"] = credit.order
                real_actors.append(person_data)

        # 覆盖 JSON 数据
        if real_creators:
            tv_data["creators"] = real_creators
        if real_directors:
            tv_data["directors"] = real_directors
        if real_actors:
            tv_data["actors"] = real_actors

    except Exception as e:
        logger.error(f"Failed to load real credits for TV {tv_id}: {e}")
        # 如果加载失败，保留原有的 JSON 数据作为回退

    # 计算总数
    count_query = (
        select(func.count())
        .select_from(PTResource)
        .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
        .where(
            ResourceMapping.unified_table_name == "unified_tv_series",
            ResourceMapping.unified_resource_id == tv_id
        )
    )
    count_result = await db.execute(count_query)
    total_pt_resources = count_result.scalar_one()

    # 分页查询PT资源
    skip = (pt_page - 1) * pt_page_size
    mappings_query = (
        select(PTResource)
        .options(joinedload(PTResource.site))  # 预加载站点关系
        .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
        .where(
            ResourceMapping.unified_table_name == "unified_tv_series",
            ResourceMapping.unified_resource_id == tv_id
        )
        .order_by(
            PTResource.published_at.desc(),  # 按发布时间倒序（最新在前）
        )
        .offset(skip)
        .limit(pt_page_size)
    )
    mappings_result = await db.execute(mappings_query)
    pt_resources = mappings_result.scalars().all()

    # 查询所有PT资源的下载状态
    pt_resource_ids = [r.id for r in pt_resources]
    download_status_map = {}
    if pt_resource_ids:
        download_query = select(DownloadTask.pt_resource_id, DownloadTask.status).where(
            DownloadTask.pt_resource_id.in_(pt_resource_ids)
        )
        download_result = await db.execute(download_query)
        download_status_map = {row[0]: row[1] for row in download_result.all()}

    # 构建 PT 资源列表，添加站点名称和下载状态
    pt_resources_list = []
    for r in pt_resources:
        response_item = PTResourceResponse.model_validate(r)
        response_item.site_name = r.site.name if r.site else None
        # 添加下载状态
        response_item.is_downloaded = r.id in download_status_map
        response_item.download_status = download_status_map.get(r.id)
        # 使用 mode='json' 确保正确的JSON序列化，避免List字段被序列化为数字键字典
        pt_resources_list.append(response_item.model_dump(by_alias=True, mode='json'))

    tv_data["ptResources"] = pt_resources_list
    tv_data["ptResourcesPagination"] = {
        "total": total_pt_resources,
        "page": pt_page,
        "pageSize": pt_page_size,
        "totalPages": (total_pt_resources + pt_page_size - 1) // pt_page_size
    }

    return tv_data


@router.post("/{tv_id}/refresh-resources")
async def refresh_tv_resources(
    tv_id: int,
    resource_ids: Optional[List[int]] = Query(None, description="指定要刷新的资源ID列表（为空则刷新全部）"),
    db: AsyncSession = Depends(get_db),
):
    """
    刷新电视剧关联的PT资源实时信息（异步后台任务）

    - **tv_id**: 电视剧ID
    - **resource_ids**: 可选，指定要刷新的资源ID列表（为空则刷新全部）

    更新字段：做种数、下载数、促销信息、HR规则等
    返回任务执行ID，前端可轮询任务状态

    **使用场景**：
    - 不传 resource_ids：刷新所有关联资源（适合全量更新）
    - 传入 resource_ids：只刷新指定资源（适合分页刷新当前页）
    """
    import asyncio
    from app.constants import TASK_TYPE_UNIFIED_RESOURCE_REFRESH
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.task_execution_service import TaskExecutionService

    # 检查电视剧是否存在
    tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
    if not tv:
        raise HTTPException(status_code=404, detail="电视剧不存在")

    # 确定要刷新的资源范围
    refresh_scope = f"指定的 {len(resource_ids)} 个资源" if resource_ids else "所有关联资源"

    # 创建任务执行记录
    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_UNIFIED_RESOURCE_REFRESH,
        task_name=f"刷新电视剧资源: {tv.title} ({refresh_scope})",
        handler=TASK_TYPE_UNIFIED_RESOURCE_REFRESH,
        handler_params={
            "unified_table_name": "unified_tv_series",
            "unified_resource_id": tv_id,
            "resource_ids": resource_ids  # 新增：支持指定资源ID列表
        }
    )
    execution = await TaskExecutionService.create(db, execution_data)

    # 后台执行任务（不阻塞响应）
    from app.services.task.scheduler_manager import scheduler_manager
    asyncio.create_task(
        scheduler_manager._execute_task_by_execution(execution.id)
    )

    return {
        "execution_id": execution.id,
        "tv_id": tv_id,
        "refresh_scope": refresh_scope,
        "message": "刷新任务已创建，请通过 /api/v1/task-executions/{execution_id} 查询进度"
    }


@router.post("/{tv_id}/sync-pt-resources")
async def sync_tv_pt_resources(
    tv_id: int,
    site_id: Optional[int] = Query(None, description="指定PT站点ID（为空则同步所有启用的站点）"),
    db: AsyncSession = Depends(get_db),
):
    """
    从PT站点手动同步该电视剧的资源（异步后台任务）

    - **tv_id**: 电视剧ID
    - **site_id**: 可选，指定PT站点ID（为空则同步所有启用的站点）

    使用电视剧标题作为关键字，从PT站点搜索并同步相关资源
    返回任务执行ID，前端可轮询任务状态

    **使用场景**：
    - 手动触发同步某个电视剧在PT站点的最新资源
    - 补充缺失的资源链接
    """
    import asyncio
    from app.constants import TASK_TYPE_PT_RESOURCE_SYNC
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.task_execution_service import TaskExecutionService

    # 检查电视剧是否存在
    tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
    if not tv:
        raise HTTPException(status_code=404, detail="电视剧不存在")

    # 如果指定了站点，检查站点是否存在
    if site_id:
        from app.models.pt_site import PTSite
        site = await db.get(PTSite, site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"站点ID {site_id} 不存在")
        site_name = site.name
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

    # 使用电视剧标题作为关键字
    keyword = tv.title

    # 创建任务执行记录
    task_name = f"同步PT资源: {keyword} ({site_name})"

    if site_id:
        # 指定站点同步
        execution_data = TaskExecutionCreate(
            task_type=TASK_TYPE_PT_RESOURCE_SYNC,
            task_name=task_name,
            handler=TASK_TYPE_PT_RESOURCE_SYNC,
            handler_params={
                "site_id": site_id,
                "sync_type": "manual",
                "max_pages": 5,  # 限制最多同步5页
                "keyword": keyword,
                "mode": "normal",  # 仅同步电视剧资源
            }
        )
        execution = await TaskExecutionService.create(db, execution_data)

        # 后台执行任务
        from app.services.task.scheduler_manager import scheduler_manager
        asyncio.create_task(
            scheduler_manager._execute_task_by_execution(execution.id)
        )

        return {
            "execution_id": execution.id,
            "tv_id": tv_id,
            "keyword": keyword,
            "site_id": site_id,
            "message": f"同步任务已创建，正在从 {site_name} 搜索资源"
        }
    else:
        # 同步所有启用的站点
        execution_ids = []
        for site in sites:
            execution_data = TaskExecutionCreate(
                task_type=TASK_TYPE_PT_RESOURCE_SYNC,
                task_name=f"同步PT资源: {keyword} ({site.name})",
                handler=TASK_TYPE_PT_RESOURCE_SYNC,
                handler_params={
                    "site_id": site.id,
                    "sync_type": "manual",
                    "max_pages": 3,
                    "keyword": keyword,
                    "mode": "normal",
                }
            )
            execution = await TaskExecutionService.create(db, execution_data)
            execution_ids.append(execution.id)

            # 后台执行任务
            from app.services.task.scheduler_manager import scheduler_manager
            asyncio.create_task(
                scheduler_manager._execute_task_by_execution(execution.id)
            )

        return {
            "execution_ids": execution_ids,
            "tv_id": tv_id,
            "keyword": keyword,
            "sites_count": len(sites),
            "message": f"已创建 {len(sites)} 个同步任务，正在从所有启用站点搜索资源"
        }


@router.put("/{tv_id}")
async def update_tv_series(
    tv_id: int,
    tv_data: UnifiedTVUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新电视剧信息

    - **tv_id**: 电视剧ID

    可更新的字段：
    - 外部ID：tmdb_id, imdb_id, tvdb_id, douban_id
    - 标题：title, original_title, aka
    - 基础信息：year, first_air_date, last_air_date, status
    - 季数集数：number_of_seasons, number_of_episodes
    - 评分：rating_tmdb, rating_douban, rating_imdb 及对应的 votes
    - 分类：genres, tags, languages, countries, networks
    - 内容：overview, tagline, certification
    - 图片：poster_url, backdrop_url

    注意：外部ID有唯一约束，如果更新的ID已被其他电视剧使用，将返回错误
    """
    # 检查电视剧是否存在
    tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
    if not tv:
        raise HTTPException(status_code=404, detail="电视剧不存在")

    # 检查外部ID是否冲突
    update_data = tv_data.model_dump(exclude_unset=True)

    # 检查 IMDB ID 冲突
    if "imdb_id" in update_data and update_data["imdb_id"]:
        existing = await UnifiedTVSeriesService.get_by_imdb_id(db, update_data["imdb_id"])
        if existing and existing.id != tv_id:
            raise HTTPException(
                status_code=400,
                detail=f"IMDB ID {update_data['imdb_id']} 已被其他电视剧使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    # 检查 TMDB ID 冲突
    if "tmdb_id" in update_data and update_data["tmdb_id"]:
        existing = await UnifiedTVSeriesService.get_by_tmdb_id(db, update_data["tmdb_id"])
        if existing and existing.id != tv_id:
            raise HTTPException(
                status_code=400,
                detail=f"TMDB ID {update_data['tmdb_id']} 已被其他电视剧使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    # 检查 TVDB ID 冲突
    if "tvdb_id" in update_data and update_data["tvdb_id"]:
        existing = await UnifiedTVSeriesService.get_by_tvdb_id(db, update_data["tvdb_id"])
        if existing and existing.id != tv_id:
            raise HTTPException(
                status_code=400,
                detail=f"TVDB ID {update_data['tvdb_id']} 已被其他电视剧使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    # 检查豆瓣 ID 冲突
    if "douban_id" in update_data and update_data["douban_id"]:
        existing = await UnifiedTVSeriesService.get_by_douban_id(db, update_data["douban_id"])
        if existing and existing.id != tv_id:
            raise HTTPException(
                status_code=400,
                detail=f"豆瓣 ID {update_data['douban_id']} 已被其他电视剧使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    try:
        updated_tv = await UnifiedTVSeriesService.update_tv_series(db, tv_id, update_data)
        if not updated_tv:
            raise HTTPException(status_code=500, detail="更新失败")

        return {
            "message": "电视剧信息更新成功",
            "tv": UnifiedTVResponse.model_validate(updated_tv).model_dump(by_alias=True)
        }
    except Exception as e:
        logger.error(f"Error updating TV series {tv_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新电视剧信息失败: {str(e)}")


@router.post("/{tv_id}/refresh")
async def refresh_tv_metadata(
    tv_id: int,
    source: str = Query(..., description="数据源: tmdb 或 douban"),
    db: AsyncSession = Depends(get_db),
):
    """
    从指定数据源刷新电视剧元数据

    - **tv_id**: 电视剧ID
    - **source**: 数据源（tmdb 或 douban）

    智能合并策略：
    - 评分/投票数/类型：始终用最新数据覆盖
    - 标题/简介/图片等：仅当当前值为空时填充
    """
    if source not in ("tmdb", "douban"):
        raise HTTPException(status_code=400, detail="source 参数必须是 tmdb 或 douban")

    tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
    if not tv:
        raise HTTPException(status_code=404, detail="电视剧不存在")

    try:
        updated_tv, updated_fields = await MetadataRefreshService.refresh_tv_metadata(
            db, tv_id, source
        )
        return {
            "message": f"已从 {source.upper()} 刷新元数据",
            "source": source,
            "updatedFields": updated_fields,
            "tv": UnifiedTVResponse.model_validate(updated_tv).model_dump(by_alias=True)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error refreshing TV {tv_id} metadata from {source}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刷新元数据失败: {str(e)}")
