# -*- coding: utf-8 -*-
"""
统一电影资源API接口
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.unified_movie import UnifiedMovieResponse, UnifiedMovieWithPTResources, UnifiedMovieListResponse, UnifiedMovieUpdate
from app.services.identification.unified_movie_service import UnifiedMovieService
from app.services.identification.metadata_refresh_service import MetadataRefreshService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unified/movies", tags=["统一电影资源"])


@router.get("", response_model=dict)
async def get_movies(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    has_free_resource: Optional[bool] = Query(None, description="是否有免费资源"),
    year: Optional[int] = Query(None, description="年份"),
    genre: Optional[str] = Query(None, description="类型"),
    country: Optional[str] = Query(None, description="国家/地区"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段: created_at, rating, year, title"),
    order: str = Query("desc", description="排序方向: asc, desc"),
    min_rating: Optional[float] = Query(None, description="最低评分"),
    trending_collection: Optional[str] = Query(None, description="榜单类型（如: douban_top250）"),
    exclude_genre: Optional[str] = Query(None, description="排除的类型（如'动画'）"),
    has_local: Optional[bool] = Query(None, description="是否有本地文件"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取统一电影资源列表

    支持筛选和搜索：
    - **has_free_resource**: 是否有免费PT资源
    - **year**: 年份
    - **genre**: 类型（如"剧情"、"动作"）
    - **country**: 国家/地区
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

    try:
        movies, total = await UnifiedMovieService.get_list(
            db=db,
            skip=skip,
            limit=page_size,
            has_free_resource=has_free_resource,
            year=year,
            genre=genre,
            country=country,
            search=search,
            sort_by=sort_by,
            order=order,
            min_rating=min_rating,
            trending_collection=trending_collection,
            exclude_genre=exclude_genre,
            has_local=has_local,
        )
    except Exception as e:
        logger.error(f"Error getting movies list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取电影列表失败: {str(e)}")


    return {
        "items": [UnifiedMovieListResponse.model_validate(m).model_dump(by_alias=True) for m in movies if m is not None],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{movie_id}")
async def get_movie(
    movie_id: int,
    pt_page: int = Query(1, ge=1, description="PT资源页码"),
    pt_page_size: int = Query(20, ge=1, le=100, description="PT资源每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取统一电影资源详情（含关联的PT资源列表，支持分页）

    - **movie_id**: 电影ID
    - **pt_page**: PT资源页码（默认1）
    - **pt_page_size**: PT资源每页数量（默认20，最大100）

    返回电影详情和关联的PT资源列表（分页）
    """
    movie = await UnifiedMovieService.get_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    # 构建响应数据（使用 camelCase）
    try:
        movie_data = UnifiedMovieResponse.model_validate(movie).model_dump(by_alias=True)
    except Exception as e:
        logger.error(f"Failed to serialize movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail=f"电影数据序列化失败: {str(e)}")

    # 获取关联的PT资源（分页）
    from app.models.resource_mapping import ResourceMapping
    from app.models.pt_resource import PTResource
    from app.models.download_task import DownloadTask
    from app.models.unified_person import MovieCredit
    from app.schemas.pt_resource import PTResourceResponse
    from sqlalchemy import select, func
    from sqlalchemy.orm import joinedload, selectinload

    # --- 修复：从其实体关系表加载演职员信息，确保使用本地 Person ID ---
    try:
        credits_query = (
            select(MovieCredit)
            .options(selectinload(MovieCredit.person))
            .where(MovieCredit.movie_id == movie_id)
            .order_by(MovieCredit.order.asc())
        )
        credits_result = await db.execute(credits_query)
        credits_list = credits_result.scalars().all()

        real_directors = []
        real_actors = []
        real_writers = []

        for credit in credits_list:
            if not credit.person:
                continue
            
            person_data = {
                "id": credit.person.id, # 这里是关键：使用本地数据库ID
                "name": credit.person.name,
                "douban_id": credit.person.douban_id,
                "imdb_id": credit.person.imdb_id,
                "tmdb_id": credit.person.tmdb_id,
                "thumb_url": credit.person.profile_url,
            }

            if credit.job == "Director":
                real_directors.append(person_data)
            elif credit.job == "Actor":
                person_data["character"] = credit.character
                person_data["order"] = credit.order
                real_actors.append(person_data)
            elif credit.job == "Writer":
                real_writers.append(person_data)

        # 覆盖 JSON 数据
        if real_directors:
            movie_data["directors"] = real_directors
        if real_actors:
            movie_data["actors"] = real_actors
        if real_writers:
            movie_data["writers"] = real_writers
            
    except Exception as e:
        logger.error(f"Failed to load real credits for movie {movie_id}: {e}")
        # 如果加载失败，保留原有的 JSON 数据作为回退



    # 计算总数
    count_query = (
        select(func.count())
        .select_from(PTResource)
        .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
        .where(
            ResourceMapping.unified_table_name == "unified_movies",
            ResourceMapping.unified_resource_id == movie_id
        )
    )
    count_result = await db.execute(count_query)
    total_pt_resources = count_result.scalar() or 0

    # 分页查询PT资源
    skip = (pt_page - 1) * pt_page_size
    mappings_query = (
        select(PTResource)
        .options(joinedload(PTResource.site))  # 预加载站点关系
        .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
        .where(
            ResourceMapping.unified_table_name == "unified_movies",
            ResourceMapping.unified_resource_id == movie_id
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
        try:
            response_item = PTResourceResponse.model_validate(r)
            response_item.site_name = r.site.name if r.site else None
            # 添加下载状态
            response_item.is_downloaded = r.id in download_status_map
            response_item.download_status = download_status_map.get(r.id)
            # 使用 mode='json' 确保正确的JSON序列化，避免List字段被序列化为数字键字典
            pt_resources_list.append(response_item.model_dump(by_alias=True, mode='json'))
        except Exception as e:
            logger.error(f"Failed to serialize PT resource {r.id}: {e}")
            # 跳过有问题的资源，继续处理其他资源
            continue

    movie_data["ptResources"] = pt_resources_list
    movie_data["ptResourcesPagination"] = {
        "total": total_pt_resources,
        "page": pt_page,
        "pageSize": pt_page_size,
        "totalPages": (total_pt_resources + pt_page_size - 1) // pt_page_size
    }

    return movie_data


@router.post("/{movie_id}/refresh-resources")
async def refresh_movie_resources(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    刷新电影关联的所有PT资源实时信息

    - **movie_id**: 电影ID

    更新字段：做种数、下载数、促销信息、HR规则等
    """
    # 检查电影是否存在
    movie = await UnifiedMovieService.get_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    # 获取关联的PT资源ID列表
    from app.models.resource_mapping import ResourceMapping
    from app.models.pt_resource import PTResource
    from sqlalchemy import select

    mappings_query = (
        select(PTResource.id)
        .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
        .where(
            ResourceMapping.unified_table_name == "unified_movies",
            ResourceMapping.unified_resource_id == movie_id
        )
    )
    mappings_result = await db.execute(mappings_query)
    pt_resource_ids = [row[0] for row in mappings_result.all()]

    if not pt_resource_ids:
        return {
            "movie_id": movie_id,
            "message": "该电影没有关联的PT资源",
            "total": 0,
            "success": 0,
            "failed": 0
        }

    # 批量刷新资源
    from app.services.pt.pt_resource_service import PTResourceService
    result = await PTResourceService.batch_refresh_resources(db, pt_resource_ids)

    # 更新电影的统计信息
    await movie.update_statistics(db)

    return {
        "movie_id": movie_id,
        "message": f"已刷新 {result['success']}/{result['total']} 个资源",
        "total": result["total"],
        "success": result["success"],
        "failed": result["failed"],
        "errors": result["errors"]
    }


@router.post("/{movie_id}/sync-pt-resources")
async def sync_movie_pt_resources(
    movie_id: int,
    site_id: Optional[int] = Query(None, description="指定PT站点ID（为空则同步所有启用的站点）"),
    db: AsyncSession = Depends(get_db),
):
    """
    从PT站点手动同步该电影的资源（异步后台任务）

    - **movie_id**: 电影ID
    - **site_id**: 可选，指定PT站点ID（为空则同步所有启用的站点）

    使用电影标题作为关键字，从PT站点搜索并同步相关资源
    返回任务执行ID，前端可轮询任务状态

    **使用场景**：
    - 手动触发同步某个电影在PT站点的最新资源
    - 补充缺失的资源链接
    """
    import asyncio
    from app.constants import TASK_TYPE_PT_RESOURCE_SYNC
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.task_execution_service import TaskExecutionService

    # 检查电影是否存在
    movie = await UnifiedMovieService.get_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

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

    # 使用电影标题作为关键字
    keyword = movie.title

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
                "mode": "normal",  # 仅同步电影资源
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
            "movie_id": movie_id,
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
            "movie_id": movie_id,
            "keyword": keyword,
            "sites_count": len(sites),
            "message": f"已创建 {len(sites)} 个同步任务，正在从所有启用站点搜索资源"
        }


@router.put("/{movie_id}")
async def update_movie(
    movie_id: int,
    movie_data: UnifiedMovieUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新电影信息

    - **movie_id**: 电影ID

    可更新的字段：
    - 外部ID：tmdb_id, imdb_id, douban_id
    - 标题：title, original_title, aka
    - 基础信息：year, release_date, runtime
    - 评分：rating_tmdb, rating_douban, rating_imdb 及对应的 votes
    - 分类：genres, tags, languages, countries
    - 内容：overview, tagline, certification
    - 图片：poster_url, backdrop_url

    注意：外部ID有唯一约束，如果更新的ID已被其他电影使用，将返回错误
    """
    # 检查电影是否存在
    movie = await UnifiedMovieService.get_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    # 检查外部ID是否冲突
    update_data = movie_data.model_dump(exclude_unset=True)

    # 检查 IMDB ID 冲突
    if "imdb_id" in update_data and update_data["imdb_id"]:
        existing = await UnifiedMovieService.get_by_imdb_id(db, update_data["imdb_id"])
        if existing and existing.id != movie_id:
            raise HTTPException(
                status_code=400,
                detail=f"IMDB ID {update_data['imdb_id']} 已被其他电影使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    # 检查 TMDB ID 冲突
    if "tmdb_id" in update_data and update_data["tmdb_id"]:
        existing = await UnifiedMovieService.get_by_tmdb_id(db, update_data["tmdb_id"])
        if existing and existing.id != movie_id:
            raise HTTPException(
                status_code=400,
                detail=f"TMDB ID {update_data['tmdb_id']} 已被其他电影使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    # 检查豆瓣 ID 冲突
    if "douban_id" in update_data and update_data["douban_id"]:
        existing = await UnifiedMovieService.get_by_douban_id(db, update_data["douban_id"])
        if existing and existing.id != movie_id:
            raise HTTPException(
                status_code=400,
                detail=f"豆瓣 ID {update_data['douban_id']} 已被其他电影使用（ID: {existing.id}, 标题: {existing.title}）"
            )

    try:
        updated_movie = await UnifiedMovieService.update_movie(db, movie_id, movie_data)
        if not updated_movie:
            raise HTTPException(status_code=500, detail="更新失败")

        return {
            "message": "电影信息更新成功",
            "movie": UnifiedMovieResponse.model_validate(updated_movie).model_dump(by_alias=True)
        }
    except Exception as e:
        logger.error(f"Error updating movie {movie_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新电影信息失败: {str(e)}")


@router.post("/{movie_id}/refresh")
async def refresh_movie_metadata(
    movie_id: int,
    source: str = Query(..., description="数据源: tmdb 或 douban"),
    db: AsyncSession = Depends(get_db),
):
    """
    从指定数据源刷新电影元数据

    - **movie_id**: 电影ID
    - **source**: 数据源（tmdb 或 douban）

    智能合并策略：
    - 评分/投票数/类型：始终用最新数据覆盖
    - 标题/简介/图片等：仅当当前值为空时填充
    """
    if source not in ("tmdb", "douban"):
        raise HTTPException(status_code=400, detail="source 参数必须是 tmdb 或 douban")

    movie = await UnifiedMovieService.get_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    try:
        updated_movie, updated_fields = await MetadataRefreshService.refresh_movie_metadata(
            db, movie_id, source
        )
        return {
            "message": f"已从 {source.upper()} 刷新元数据",
            "source": source,
            "updatedFields": updated_fields,
            "movie": UnifiedMovieResponse.model_validate(updated_movie).model_dump(by_alias=True)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error refreshing movie {movie_id} metadata from {source}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刷新元数据失败: {str(e)}")
