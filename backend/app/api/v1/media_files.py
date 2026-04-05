# -*- coding: utf-8 -*-
"""
媒体文件API路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.media_file import (
    MediaFileListResponse,
    MediaFileOrganizeRequest,
    MediaFileResponse,
    MediaFileScanRequest,
    MediaFileIdentifyRequest,
    MediaFileIdentifyResponse,
    MediaFileLinkRequest,
    MediaFileLinkResponse,
    TMDBSearchRequest,
    TMDBSearchResponse,
    TMDBCandidate,
    DoubanSearchRequest,
    DoubanSearchResponse,
    DoubanCandidate,
    MediaFileScrapeRequest,
    MediaFileScrapeResponse,
    MediaFileBatchScrapeRequest,
    MediaFileBatchScrapeResponse,
    MediaFileGenerateNFORequest,
    MediaFileGenerateNFOResponse,
    MediaFileUpdateEpisodeInfo,
    MediaFileParseFilenameResponse,
)
from app.services.mediafile.media_file_service import MediaFileService
from app.services.mediafile.media_info_service import MediaInfoService
from app.services.mediafile.media_organizer_service import MediaOrganizerService
from app.services.identification.media_identify_service import media_identify_service
from app.services.mediafile.scraper_service import scraper_service
from app.services.mediafile.organize_config_service import OrganizeConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media-files", tags=["media_files"])


@router.get("", response_model=MediaFileListResponse)
async def list_media_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    media_type: Optional[str] = None,
    file_type: Optional[str] = Query("video", description="文件类型筛选：video/subtitle/audio/other，默认只显示视频"),
    organized: Optional[bool] = None,
    directory: Optional[str] = Query(None, description="按目录前缀筛选（如：./data/downloads）"),
    resolution: Optional[str] = Query(None, description="分辨率筛选（如：1080p）"),
    mount_type: Optional[str] = Query(None, description="按挂载点类型筛选（如：download）"),
    download_task_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询媒体文件列表

    Args:
        skip: 跳过数量
        limit: 返回数量
        status: 文件状态过滤
        media_type: 媒体类型过滤
        file_type: 文件类型过滤（video/subtitle/audio/other），默认只显示视频
        organized: 是否已整理过滤
        directory: 按目录前缀筛选
        resolution: 分辨率筛选
        mount_type: 按挂载点类型筛选
        download_task_id: 下载任务ID过滤
        db: 数据库会话
        current_user: 当前用户

    Returns:
        媒体文件列表
    """
    result = await MediaFileService.list(
        db,
        skip=skip,
        limit=limit,
        status=status,
        media_type=media_type,
        file_type=file_type,
        organized=organized,
        directory=directory,
        resolution=resolution,
        mount_type=mount_type,
        download_task_id=download_task_id,
    )

    # 为每个媒体文件添加 download_task 的配置信息
    items_with_config = []
    for media_file in result["items"]:
        # 直接使用 model_validate 创建响应对象
        file_response = MediaFileResponse.model_validate(media_file)

        # 如果有关联的下载任务，添加配置ID
        if media_file.download_task:
            file_response.download_organize_config_id = media_file.download_task.organize_config_id
            file_response.download_storage_mount_id = media_file.download_task.storage_mount_id

        items_with_config.append(file_response)

    return MediaFileListResponse(total=result["total"], items=items_with_config)


@router.get("/{file_id}", response_model=MediaFileResponse)
async def get_media_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取媒体文件详情

    Args:
        file_id: 文件ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        媒体文件详情
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    from app.api.v1.media_directories import check_episode_metadata
    resp = MediaFileResponse.model_validate(media_file)
    actual_path = media_file.organized_path or media_file.file_path
    meta = check_episode_metadata(actual_path)
    resp.has_nfo = meta["has_nfo"]
    resp.has_poster = meta["has_poster"]
    return resp


@router.get("/{file_id}/episode-metadata")
async def get_episode_metadata(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取剧集文件的完整元数据：解析 NFO 内容 + 缩略图代理 URL。
    用于在文件管理页面的剧集详情面板中展示实际内容。
    """
    import os
    from pathlib import Path as _Path
    from urllib.parse import quote
    from app.services.mediafile.nfo_parser_service import NFOParserService

    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    file_path = media_file.organized_path or media_file.file_path
    result: dict = {
        "has_nfo": False,
        "has_poster": False,
        "poster_url": None,
        "nfo_data": None,
        "file_path": media_file.file_path,
        "organized_path": media_file.organized_path,
        "nfo_path": None,
        "poster_file_path": None,
        "video_codec": media_file.video_codec,
        "duration": media_file.duration,
        "organized": media_file.organized,
        "organize_mode": media_file.organize_mode,
        "status": media_file.status,
        "media_type": media_file.media_type,
        "sub_title": media_file.sub_title,
    }

    if not file_path or not os.path.exists(file_path):
        return result

    p = _Path(file_path)
    stem = p.stem
    parent = p.parent

    # NFO：{stem}.nfo
    nfo_path = parent / f"{stem}.nfo"
    if nfo_path.exists():
        result["has_nfo"] = True
        result["nfo_path"] = str(nfo_path)
        try:
            result["nfo_data"] = await NFOParserService.parse_nfo(str(nfo_path))
        except Exception:
            pass

    # 缩略图：常见命名约定
    for name in (
        f"{stem}-thumb.jpg", f"{stem}-thumb.jpeg", f"{stem}-thumb.png",
        f"{stem}-thumb.webp",
        f"{stem}.jpg", f"{stem}.jpeg", f"{stem}.png",
    ):
        thumb = parent / name
        if thumb.exists():
            result["has_poster"] = True
            result["poster_file_path"] = str(thumb)
            encoded = quote(str(thumb).replace("\\", "/"), safe="")
            result["poster_url"] = f"/api/v1/media-directories/image?path={encoded}"
            break

    return result


@router.post("/scan")
async def scan_directory(
    request: MediaFileScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    扫描目录并创建媒体文件记录（后台任务）

    Args:
        request: 扫描请求
        db: 数据库会话
        current_user: 当前用户

    Returns:
        任务执行ID，可用于查询进度
    """
    try:
        from app.constants import TASK_TYPE_MEDIA_FILE_SCAN
        from app.schemas.task_execution import TaskExecutionCreate
        from app.services.task.task_execution_service import TaskExecutionService
        from app.services.task.scheduler_manager import scheduler_manager
        import asyncio

        # 创建任务执行记录
        execution_data = TaskExecutionCreate(
            task_type=TASK_TYPE_MEDIA_FILE_SCAN,
            task_name=f"扫描目录: {request.directory} ({request.scan_mode})",
            handler=TASK_TYPE_MEDIA_FILE_SCAN,  # 使用任务类型作为 handler
            handler_params={
                "directory": request.directory,
                "mount_type": request.mount_type,
                "recursive": request.recursive,
                "media_type": request.media_type,
                "scan_mode": request.scan_mode or "full",
            },
            priority=0,
        )

        execution = await TaskExecutionService.create(db, execution_data)

        # 在后台执行任务
        asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

        return {
            "status": "success",
            "message": "扫描任务已创建",
            "execution_id": execution.id,
        }
    except Exception as e:
        logger.exception(f"创建扫描任务失败: {request.directory}")
        raise HTTPException(status_code=500, detail=f"创建扫描任务失败: {str(e)}")


@router.post("/{file_id}/extract-mediainfo")
async def extract_mediainfo(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    提取媒体文件的技术信息

    Args:
        file_id: 文件ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        提取结果
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    try:
        success = await MediaInfoService.extract_and_update(db, media_file)
        if success:
            return {
                "status": "success",
                "message": "MediaInfo提取成功",
                "media_file": MediaFileResponse.model_validate(media_file),
            }
        else:
            return {
                "status": "failed",
                "message": "MediaInfo提取失败，请检查日志",
            }
    except Exception as e:
        logger.exception(f"提取MediaInfo失败: {file_id}")
        raise HTTPException(status_code=500, detail=f"提取MediaInfo失败: {str(e)}")


@router.post("/organize")
async def organize_media_files(
    request: MediaFileOrganizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量整理媒体文件

    Args:
        request: 整理请求
        db: 数据库会话
        current_user: 当前用户

    Returns:
        整理结果
    """
    try:
        result = await MediaOrganizerService.batch_organize(
            db,
            media_file_ids=request.file_ids,
            config_id=request.config_id,
            dry_run=request.dry_run,
            force=request.force,
            storage_mount_id=request.storage_mount_id,
        )
        return result
    except Exception as e:
        logger.exception("批量整理文件失败")
        raise HTTPException(status_code=500, detail=f"整理失败: {str(e)}")


@router.post("/{file_id}/organize")
async def organize_single_file(
    file_id: int,
    config_id: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
    season_number: Optional[int] = None,
    episode_number: Optional[int] = None,
    storage_mount_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    整理单个媒体文件（支持手动指定季集）

    Args:
        file_id: 文件ID
        config_id: 配置ID（可选）
        dry_run: 是否仅模拟运行
        force: 强制重新整理（忽略已整理状态）
        season_number: 季数（可选，用于手动指定）
        episode_number: 集数（可选，用于手动指定）
        db: 数据库会话
        current_user: 当前用户

    Returns:
        整理结果
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    # 如果提供了季集参数，更新到文件对象
    if season_number is not None:
        media_file.season_number = season_number
    if episode_number is not None:
        media_file.episode_number = episode_number

    # 如果提供了手动季集，标记为手动指定
    if season_number is not None or episode_number is not None:
        if not media_file.match_detail:
            media_file.match_detail = {}
        media_file.match_detail["manual_season_episode"] = True
        await db.commit()

    try:
        from app.services.mediafile.organize_config_service import OrganizeConfigService

        config = None
        if config_id:
            config = await OrganizeConfigService.get_by_id(db, config_id)
            if not config:
                raise HTTPException(status_code=404, detail="配置不存在")

        result = await MediaOrganizerService.organize_media_file(
            db, media_file, config, dry_run, force, storage_mount_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"整理文件失败: {file_id}")
        raise HTTPException(status_code=500, detail=f"整理失败: {str(e)}")


@router.delete("/{file_id}")
async def delete_media_file(
    file_id: int,
    delete_physical_file: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除媒体文件记录

    Args:
        file_id: 文件ID
        delete_physical_file: 是否删除物理文件
        db: 数据库会话
        current_user: 当前用户

    Returns:
        删除结果
    """
    success = await MediaFileService.delete(db, file_id, delete_physical_file)
    if not success:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    return {"status": "success", "message": "删除成功"}


# ========== 文件信息编辑API ==========


@router.put("/{file_id}/episode-info")
async def update_episode_info(
    file_id: int,
    request: MediaFileUpdateEpisodeInfo,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新媒体文件的季集信息

    用于手动维护集数、季数、集标题
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    if request.season_number is not None:
        media_file.season_number = request.season_number
    if request.episode_number is not None:
        media_file.episode_number = request.episode_number
    if request.episode_title is not None:
        media_file.episode_title = request.episode_title

    await db.commit()
    return {"success": True, "message": "更新成功"}


@router.get("/{file_id}/parse-filename", response_model=MediaFileParseFilenameResponse)
async def parse_filename(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    从文件名解析季集信息

    使用guessit解析文件名，返回解析到的季数、集数等信息
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    from app.services.common.filename_parser_service import FilenameParserService

    parsed = FilenameParserService.parse_media_file(
        media_file.organized_path or media_file.file_path
    )

    return MediaFileParseFilenameResponse(
        season=parsed.get("season"),
        episode=parsed.get("episode"),
        title=parsed.get("title"),
        episode_title=parsed.get("episode_title"),
        year=parsed.get("year"),
        resolution=parsed.get("resolution"),
    )


# ========== 识别相关API ==========


@router.post("/{file_id}/identify", response_model=MediaFileIdentifyResponse)
async def identify_media_file(
    file_id: int,
    request: MediaFileIdentifyRequest = MediaFileIdentifyRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    识别媒体文件

    通过文件名解析和TMDB搜索识别媒体文件内容

    Args:
        file_id: 文件ID
        request: 识别请求参数
        db: 数据库会话
        current_user: 当前用户

    Returns:
        识别结果，包含候选列表
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    try:
        result = await media_identify_service.identify_media_file(
            db, media_file, request.force_search
        )

        # 转换候选项为Schema格式
        candidates = []
        match_source = result.get("match_source")
        adult_sources = {"adult_product_number", "dmm", "simplified"}
        if match_source not in adult_sources:
            for item in result.get("candidates", []):
                candidate = TMDBCandidate(
                    tmdb_id=item.get("tmdb_id"),
                    title=item.get("title"),
                    original_title=item.get("original_title"),
                    year=item.get("year"),
                    overview=item.get("overview"),
                    poster_url=item.get("poster_url"),
                    backdrop_url=item.get("backdrop_url"),
                    rating_tmdb=item.get("rating_tmdb"),
                    votes_tmdb=item.get("votes_tmdb"),
                    genres=item.get("genres"),
                    media_type=item.get("media_type", "movie"),
                )
                candidates.append(candidate)

        return MediaFileIdentifyResponse(
            success=result.get("success", False),
            candidates=candidates,
            auto_matched=result.get("auto_matched", False),
            matched_id=result.get("matched_id"),
            match_source=result.get("match_source"),
            parsed_info=result.get("parsed_info"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.exception(f"识别媒体文件失败: {file_id}")
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


@router.post("/{file_id}/link", response_model=MediaFileLinkResponse)
async def link_media_file_to_resource(
    file_id: int,
    request: MediaFileLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    将媒体文件关联到统一资源

    根据TMDB ID获取元数据并关联到统一资源表

    Args:
        file_id: 文件ID
        request: 关联请求（包含tmdb_id和media_type）
        db: 数据库会话
        current_user: 当前用户

    Returns:
        关联结果
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    try:
        # 获取TMDB适配器（从数据库配置）
        tmdb_adapter = await media_identify_service._get_tmdb_adapter(db)

        # 从TMDB获取完整元数据
        if request.media_type == "movie":
            tmdb_data = await tmdb_adapter.get_movie_details(request.tmdb_id)
        elif request.media_type in ("tv", "episode"):
            tmdb_data = await tmdb_adapter.get_tv_details(request.tmdb_id)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的媒体类型: {request.media_type}")

        if not tmdb_data:
            raise HTTPException(status_code=404, detail="TMDB数据获取失败")

        # 关联到统一资源
        unified_id = await media_identify_service.link_to_unified_resource(
            db, media_file, tmdb_data, request.media_type
        )

        if unified_id:
            return MediaFileLinkResponse(
                success=True,
                unified_resource_id=unified_id,
                message=f"成功关联到统一资源 (ID: {unified_id})",
            )
        else:
            return MediaFileLinkResponse(
                success=False, unified_resource_id=None, message="关联失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"关联媒体文件失败: {file_id}")
        raise HTTPException(status_code=500, detail=f"关联失败: {str(e)}")


@router.post("/search-tmdb", response_model=TMDBSearchResponse)
async def search_tmdb(
    request: TMDBSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动搜索TMDB

    用于用户手动搜索和选择正确的匹配项

    Args:
        request: 搜索请求（标题、年份、类型）
        db: 数据库会话
        current_user: 当前用户

    Returns:
        搜索结果列表
    """
    try:
        results = await media_identify_service.search_and_get_candidates(
            db, request.title, request.year, request.media_type
        )

        # 转换为Schema格式
        candidates = []
        for item in results:
            candidate = TMDBCandidate(
                tmdb_id=item.get("tmdb_id"),
                title=item.get("title"),
                original_title=item.get("original_title"),
                year=item.get("year"),
                overview=item.get("overview"),
                poster_url=item.get("poster_url"),
                backdrop_url=item.get("backdrop_url"),
                rating_tmdb=item.get("rating_tmdb"),
                votes_tmdb=item.get("votes_tmdb"),
                genres=item.get("genres"),
                media_type=request.media_type,
            )
            candidates.append(candidate)

        return TMDBSearchResponse(results=candidates, total=len(candidates))
    except Exception as e:
        logger.exception(f"搜索TMDB失败: {request.title}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/search-douban", response_model=DoubanSearchResponse)
async def search_douban(
    request: DoubanSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动搜索豆瓣

    用于用户手动搜索豆瓣获取候选列表

    Args:
        request: 搜索请求（标题、年份、类型）
        db: 数据库会话
        current_user: 当前用户

    Returns:
        搜索结果列表
    """
    try:
        from app.adapters.metadata.douban_adapter import DoubanAdapter

        douban_adapter = DoubanAdapter({"timeout": 30, "max_retries": 3})
        results = await douban_adapter.search_by_title(
            title=request.title,
            year=request.year,
            media_type=request.media_type,
        )

        candidates = []
        for item in results:
            title = item.get("title") or ""
            if not title:
                continue
            candidate = DoubanCandidate(
                douban_id=str(item.get("douban_id") or ""),
                title=title,
                year=item.get("year"),
                overview=item.get("overview") or "",
                poster_url=item.get("poster_url"),
                rating_douban=item.get("rating_douban"),
                media_type=item.get("media_type"),
            )
            candidates.append(candidate)

        return DoubanSearchResponse(results=candidates, total=len(candidates))
    except Exception as e:
        logger.exception(f"搜索豆瓣失败: {request.title}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ========== 刮削相关API ==========


@router.post("/{file_id}/scrape", response_model=MediaFileScrapeResponse)
async def scrape_media_file(
    file_id: int,
    request: MediaFileScrapeRequest = MediaFileScrapeRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    刮削媒体文件

    下载海报、背景图并生成NFO文件

    Args:
        file_id: 文件ID
        request: 刮削请求参数
        db: 数据库会话
        current_user: 当前用户

    Returns:
        刮削结果
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    # 如果 media_type 为 unknown，尝试从所属目录继承
    if media_file.media_type == "unknown" and media_file.media_directory_id:
        from app.services.mediafile.media_directory_service import MediaDirectoryService
        directory = await MediaDirectoryService.get_by_id(db, media_file.media_directory_id)
        if directory and directory.media_type and directory.media_type != "unknown":
            media_file.media_type = directory.media_type
            db.add(media_file)
            await db.flush()

    # 获取配置
    config = None
    if request.config_id:
        config = await OrganizeConfigService.get_by_id(db, request.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
    else:
        # 使用默认配置
        config = await OrganizeConfigService.get_default(db, media_file.media_type)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"未找到媒体类型 {media_file.media_type} 的默认配置",
            )

    try:
        result = await scraper_service.scrape_media_file(db, media_file, config, force=request.force)
        return MediaFileScrapeResponse(**result)
    except Exception as e:
        logger.exception(f"刮削媒体文件失败: {file_id}")
        raise HTTPException(status_code=500, detail=f"刮削失败: {str(e)}")


@router.post("/batch-scrape", response_model=MediaFileBatchScrapeResponse)
async def batch_scrape_media_files(
    request: MediaFileBatchScrapeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量刮削媒体文件

    Args:
        request: 批量刮削请求
        db: 数据库会话
        current_user: 当前用户

    Returns:
        批量刮削结果
    """
    # 获取配置
    config = None
    if request.config_id:
        config = await OrganizeConfigService.get_by_id(db, request.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

    try:
        result = await scraper_service.batch_scrape(db, request.file_ids, config)
        return MediaFileBatchScrapeResponse(**result)
    except Exception as e:
        logger.exception("批量刮削媒体文件失败")
        raise HTTPException(status_code=500, detail=f"批量刮削失败: {str(e)}")


@router.post("/{file_id}/generate-nfo", response_model=MediaFileGenerateNFOResponse)
async def generate_nfo_for_media_file(
    file_id: int,
    request: MediaFileGenerateNFORequest = MediaFileGenerateNFORequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    为媒体文件生成NFO文件

    仅生成NFO，不下载图片

    Args:
        file_id: 文件ID
        request: 生成NFO请求参数
        db: 数据库会话
        current_user: 当前用户

    Returns:
        生成结果
    """
    media_file = await MediaFileService.get_by_id(db, file_id)
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    # 获取配置
    config = None
    if request.config_id:
        config = await OrganizeConfigService.get_by_id(db, request.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
    else:
        # 使用默认配置
        config = await OrganizeConfigService.get_default(db, media_file.media_type)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"未找到媒体类型 {media_file.media_type} 的默认配置",
            )

    try:
        result = await scraper_service.generate_nfo_only(db, media_file, config, force=request.force)
        return MediaFileGenerateNFOResponse(**result)
    except Exception as e:
        logger.exception(f"生成NFO失败: {file_id}")
        raise HTTPException(status_code=500, detail=f"生成NFO失败: {str(e)}")
