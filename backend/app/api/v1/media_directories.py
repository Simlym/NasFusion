# -*- coding: utf-8 -*-
"""
媒体目录API路由
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.core.dependencies import get_current_user, get_db
from app.models import User, MediaDirectory
from app.services.mediafile.media_directory_service import MediaDirectoryService
from app.services.mediafile.nfo_parser_service import NFOParserService
from app.services.common.system_setting_service import SystemSettingService
from app.schemas.media_directory import (
    MediaDirectoryResponse,
    DirectoryTreeNode,
    DirectoryDetailResponse,
    SyncFromFilesRequest,
    SyncFromFilesResponse,
    DetectIssuesRequest,
    DetectIssuesResponse,
    MediaDirectoryLinkRequest,
)
from app.constants import MEDIA_TYPE_ADULT

router = APIRouter(prefix="/media-directories", tags=["media_directories"])


def check_episode_metadata(file_path: Optional[str]) -> dict:
    """
    实时检查剧集文件旁边是否存在 NFO 和缩略图文件。
    NFO:  {stem}.nfo
    图片:  {stem}-thumb.jpg / {stem}.jpg 等常见命名
    """
    import os
    from pathlib import Path as _Path

    result = {"has_nfo": False, "has_poster": False, "has_subtitle": False, "subtitle_paths": []}
    if not file_path or not os.path.exists(file_path):
        return result

    p = _Path(file_path)
    stem = p.stem
    parent = p.parent

    # NFO
    if (parent / f"{stem}.nfo").exists():
        result["has_nfo"] = True

    # 缩略图（常见命名规则）
    for name in (
        f"{stem}-thumb.jpg", f"{stem}-thumb.jpeg", f"{stem}-thumb.png",
        f"{stem}-thumb.webp",
        f"{stem}.jpg", f"{stem}.jpeg", f"{stem}.png",
    ):
        if (parent / name).exists():
            result["has_poster"] = True
            break

    # 外挂字幕文件
    subtitle_exts = (".srt", ".ass", ".ssa", ".sub", ".idx", ".sup", ".vtt")
    for child in parent.iterdir():
        if child.is_file() and child.stem.startswith(stem) and child.suffix.lower() in subtitle_exts:
            result["has_subtitle"] = True
            result["subtitle_paths"].append(str(child))

    return result


def convert_file_path_to_url(file_path: Optional[str]) -> Optional[str]:
    """
    将文件系统路径转换为代理访问URL
    
    不再依赖于路径字符串本身的结构，而是通过后端的 image 代理接口进行访问。
    """
    if not file_path:
        return None

    # 规范化路径
    normalized = file_path.replace("\\", "/")
    
    from urllib.parse import quote
    # 将路径进行URL编码，以便作为查询参数传递
    # 注意：这里我们编码整个路径
    encoded_path = quote(normalized, safe="")
    
    return f"/api/v1/media-directories/image?path={encoded_path}"


@router.get("/image")
async def get_media_image(
    path: str = Query(..., description="图片的绝对路径"),
    # 此接口不需要严格权限校验以便前端直接使用 img 标签，但建议根据需求开启
    # db: AsyncSession = Depends(get_db)
):
    """
    获取媒体图片代理
    
    通过绝对路径直接返回图片文件流，解决 Docker 环境下挂载路径不确定导致的静态挂载失效问题。
    """
    from urllib.parse import unquote
    import os
    
    decoded_path = unquote(path)
    
    if not os.path.exists(decoded_path):
        raise HTTPException(status_code=404, detail="图片不存在")
        
    if not os.path.isfile(decoded_path):
        raise HTTPException(status_code=400, detail="请求的路径不是一个文件")
        
    # TODO: 可以在此处增加路径白名单校验，确保只访问媒体库内的文件
    
    return FileResponse(decoded_path)


@router.get("/tree", response_model=List[DirectoryTreeNode])
async def get_directory_tree(
    media_type: Optional[str] = Query(None, description="媒体类型筛选"),
    parent_id: Optional[int] = Query(None, description="父目录ID"),
    load_children: bool = Query(False, description="是否预加载子目录"),
    issues: Optional[List[str]] = Query(None, description="问题筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取目录树

    - **media_type**: 可选的媒体类型筛选 (movie/tv_series/anime/...)
    - **parent_id**: 父目录ID (None表示获取根目录)
    - **load_children**: 是否递归加载子目录
    - **issues**: 问题筛选条件
    """
    # 检查用户的成人内容显示设置
    show_adult_setting = await SystemSettingService.get_by_key(db, "media_library", "show_adult_content")
    show_adult_content = show_adult_setting and show_adult_setting.value == "true"

    # 如果用户未开启成人内容显示，且请求的是成人类型，直接返回空列表
    if not show_adult_content and media_type == MEDIA_TYPE_ADULT:
        return []

    directories = await MediaDirectoryService.get_tree(
        db=db,
        media_type=media_type,
        parent_id=parent_id,
        load_children=load_children,
        issues=issues
    )

    # 如果用户未开启成人内容显示，过滤掉成人类型的目录
    if not show_adult_content:
        directories = [d for d in directories if d.media_type != MEDIA_TYPE_ADULT]

    # 批量获取子目录统计，用于前端判断是否显示展开箭头
    child_counts = {}
    if directories:
        dir_ids = [d.id for d in directories]
        # 避免在这里引入并在函数内使用的循环导入，如果 MediaDirectory 已导入则直接用
        from sqlalchemy import func
        stmt = (
            select(MediaDirectory.parent_id, func.count(MediaDirectory.id))
            .where(MediaDirectory.parent_id.in_(dir_ids))
            .group_by(MediaDirectory.parent_id)
        )
        child_counts_res = await db.execute(stmt)
        child_counts = {pid: count for pid, count in child_counts_res}

    # 转换为树形结构
    tree_nodes = []
    for directory in directories:
        # 手动构造字典，避免 children 为 None 导致验证失败
        directory_dict = {
            "id": directory.id,
            "directory_path": directory.directory_path,
            "directory_name": directory.directory_name,
            "parent_id": directory.parent_id,
            "media_type": directory.media_type,
            "unified_table_name": directory.unified_table_name,
            "unified_resource_id": directory.unified_resource_id,
            "series_name": directory.series_name,
            "season_number": directory.season_number,
            "episode_count": directory.episode_count,
            "has_nfo": directory.has_nfo,
            "nfo_path": directory.nfo_path,
            "has_poster": directory.has_poster,
            "poster_path": convert_file_path_to_url(directory.poster_path), # 确保这里也转换
            "has_backdrop": directory.has_backdrop,
            "backdrop_path": convert_file_path_to_url(directory.backdrop_path), # 确保这里也转换
            "issue_flags": directory.issue_flags or {},
            "total_files": directory.total_files,
            "total_size": directory.total_size,
            "scanned_at": directory.scanned_at,
            "created_at": directory.created_at,
            "updated_at": directory.updated_at,
            "children": [],  # 懒加载模式下，children 由前端按需加载
            "has_issues": bool(directory.issue_flags),
            "subdir_count": child_counts.get(directory.id, 0)
        }

        node = DirectoryTreeNode.model_validate(directory_dict)
        tree_nodes.append(node)

    return tree_nodes


@router.get("/{directory_id}", response_model=MediaDirectoryResponse)
async def get_directory(
    directory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取目录信息"""
    directory = await MediaDirectoryService.get_by_id(db, directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="目录不存在")

    return MediaDirectoryResponse.model_validate(directory)


@router.get("/{directory_id}/detail", response_model=DirectoryDetailResponse)
async def get_directory_detail(
    directory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取目录详情

    包含目录信息、文件列表、统计数据
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        detail = await MediaDirectoryService.get_directory_detail(db, directory_id)
        if not detail:
            raise HTTPException(status_code=404, detail="目录不存在")

        from app.schemas.media_file import MediaFileResponse

        # 实时检查元数据文件（不依赖数据库字段）
        directory = detail["directory"]

        # 使用通用的实时检查方法
        metadata = MediaDirectoryService.check_metadata_realtime(
            directory.directory_path,
            directory.season_number
        )

        # 解析 NFO 文件（如果存在）
        nfo_data = None
        if metadata["has_nfo"]:
            try:
                nfo_data = await NFOParserService.parse_nfo(metadata["nfo_path"])
            except Exception as e:
                logger.warning(f"NFO 解析失败: {metadata['nfo_path']}, 错误: {e}")

        # 更新目录对象（使用实时检查的结果）
        directory.has_nfo = metadata["has_nfo"]
        directory.nfo_path = metadata["nfo_path"]
        directory.has_poster = metadata["has_poster"]
        directory.poster_path = convert_file_path_to_url(metadata["poster_path"]) if metadata["poster_path"] else None
        directory.has_backdrop = metadata["has_backdrop"]
        directory.backdrop_path = convert_file_path_to_url(metadata["backdrop_path"]) if metadata["backdrop_path"] else None

        # 转换文件列表，处理可能的验证错误，并实时检查每个文件的 NFO/图片状态
        files_response = []
        for f in detail["files"]:
            try:
                resp = MediaFileResponse.model_validate(f)
                # 实时检查该文件旁边的 NFO 和缩略图
                actual_path = f.organized_path or f.file_path
                meta = check_episode_metadata(actual_path)
                resp.has_nfo = meta["has_nfo"]
                resp.has_poster = meta["has_poster"]
                resp.has_subtitle = meta.get("has_subtitle", False)
                resp.subtitle_paths = meta.get("subtitle_paths") or None
                files_response.append(resp)
            except Exception as e:
                logger.error(f"文件序列化失败: file_id={f.id}, file_path={f.file_path}, 错误: {e}")
                continue

        # 获取关联的统一资源信息
        unified_resource = None
        if directory.unified_table_name and directory.unified_resource_id:
            try:
                from app.constants import UNIFIED_TABLE_MOVIES, UNIFIED_TABLE_TV
                if directory.unified_table_name == UNIFIED_TABLE_MOVIES:
                    from app.models.unified_movie import UnifiedMovie
                    stmt = select(UnifiedMovie).where(UnifiedMovie.id == directory.unified_resource_id)
                    result = await db.execute(stmt)
                    resource = result.scalar_one_or_none()
                elif directory.unified_table_name == UNIFIED_TABLE_TV:
                    from app.models.unified_tv_series import UnifiedTVSeries
                    stmt = select(UnifiedTVSeries).where(UnifiedTVSeries.id == directory.unified_resource_id)
                    result = await db.execute(stmt)
                    resource = result.scalar_one_or_none()

                if resource:
                    unified_resource = {
                        "id": resource.id,
                        "title": resource.title,
                        "original_title": getattr(resource, 'original_title', None),
                        "year": resource.year,
                        "poster_url": getattr(resource, 'poster_url', None),
                        "backdrop_url": getattr(resource, 'backdrop_url', None),
                        "rating": getattr(resource, 'rating_tmdb', None),
                        "genres": getattr(resource, 'genres', None),
                        "overview": getattr(resource, 'overview', None),
                        "media_type": "movie" if directory.unified_table_name == UNIFIED_TABLE_MOVIES else "tv",
                    }
            except Exception as e:
                logger.warning(f"获取统一资源信息失败: {e}")

        return DirectoryDetailResponse(
            directory=MediaDirectoryResponse.model_validate(directory),
            statistics=detail["statistics"],
            files=files_response,
            nfo_data=nfo_data,
            unified_resource=unified_resource,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取目录详情失败: directory_id={directory_id}")
        raise HTTPException(status_code=500, detail=f"获取目录详情失败: {str(e)}")


@router.post("/sync", response_model=SyncFromFilesResponse)
async def sync_from_files(
    request: SyncFromFilesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从media_files表同步构建目录树

    扫描指定基础目录下的所有文件记录,构建或更新目录树结构
    """
    result = await MediaDirectoryService.sync_from_files(
        db=db,
        base_directory=request.base_directory
    )

    return SyncFromFilesResponse(**result)


@router.post("/detect-issues", response_model=DetectIssuesResponse)
async def detect_issues(
    request: DetectIssuesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    检测目录问题

    扫描目录,检测缺失海报、NFO、未识别等问题,并更新issue_flags
    支持按媒体类型过滤
    """
    # 检查用户的成人内容显示设置
    show_adult_setting = await SystemSettingService.get_by_key(db, "media_library", "show_adult_content")
    show_adult_content = show_adult_setting and show_adult_setting.value == "true"

    # 如果用户未开启成人内容显示，且请求检测成人类型，返回空结果
    if not show_adult_content and request.media_type == MEDIA_TYPE_ADULT:
        return DetectIssuesResponse(issues={}, total_issues=0)

    issues = await MediaDirectoryService.detect_issues(
        db=db,
        directory_id=request.directory_id,
        media_type=request.media_type
    )

    total_issues = sum(issues.values())

    return DetectIssuesResponse(
        issues=issues,
        total_issues=total_issues
    )


@router.put("/{directory_id}/link")
async def link_directory_to_resource(
    directory_id: int,
    request: MediaDirectoryLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将目录关联到统一资源（通过TMDB ID、豆瓣ID 或 直接关联已有统一资源）

    用于Season层维护识别信息，方便后续刮削。
    支持三种模式：
    1. 直接传 unified_table_name + unified_resource_id（关联本地已有资源）
    2. 传 tmdb_id（通过TMDB ID获取/创建资源并关联）
    3. 传 douban_id（通过豆瓣ID转换后关联）
    """
    import logging
    logger = logging.getLogger(__name__)

    directory = await MediaDirectoryService.get_by_id(db, directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="目录不存在")

    # 模式1：直接关联已有统一资源
    if request.unified_table_name and request.unified_resource_id:
        from app.constants import UNIFIED_TABLE_MOVIES, UNIFIED_TABLE_TV

        if request.unified_table_name == UNIFIED_TABLE_MOVIES:
            from app.models.unified_movie import UnifiedMovie
            unified = await db.get(UnifiedMovie, request.unified_resource_id)
        elif request.unified_table_name == UNIFIED_TABLE_TV:
            from app.models.unified_tv_series import UnifiedTVSeries
            unified = await db.get(UnifiedTVSeries, request.unified_resource_id)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的资源表: {request.unified_table_name}")

        if not unified:
            raise HTTPException(status_code=404, detail="统一资源不存在")

        directory.unified_table_name = request.unified_table_name
        directory.unified_resource_id = unified.id
        if hasattr(unified, 'title') and unified.title:
            directory.series_name = unified.title

        # 同时更新该目录下所有文件的关联
        from app.models import MediaFile
        files_result = await db.execute(
            select(MediaFile).where(MediaFile.media_directory_id == directory_id)
        )
        files = files_result.scalars().all()
        media_type = "movie" if request.unified_table_name == UNIFIED_TABLE_MOVIES else "tv"
        for f in files:
            if not f.unified_resource_id:
                f.unified_table_name = request.unified_table_name
                f.unified_resource_id = unified.id
                if f.media_type in ("unknown", None):
                    f.media_type = media_type

        await db.commit()

        return {
            "success": True,
            "unified_resource_id": unified.id,
            "unified_table_name": request.unified_table_name,
            "title": getattr(unified, 'title', None),
            "message": f"成功关联到 {getattr(unified, 'title', unified.id)}"
        }

    # 模式2/3：通过TMDB/豆瓣ID
    if not request.tmdb_id and not request.douban_id:
        raise HTTPException(status_code=400, detail="请提供 tmdb_id、douban_id 或 unified_table_name + unified_resource_id")

    try:
        from app.services.identification.media_identify_service import media_identify_service

        tmdb_id = request.tmdb_id

        # 如果只提供了豆瓣ID，尝试转换为TMDB ID
        if not tmdb_id and request.douban_id:
            tmdb_adapter = await media_identify_service._get_tmdb_adapter(db)
            # 先通过豆瓣获取信息，再搜索TMDB
            from app.adapters.metadata.douban import DoubanAdapter
            douban_adapter = DoubanAdapter()
            douban_data = await douban_adapter.get_movie_details(request.douban_id)
            if douban_data and douban_data.get("title"):
                results = await tmdb_adapter.search_tv(douban_data["title"], year=douban_data.get("year"))
                if results:
                    tmdb_id = results[0].get("tmdb_id")

        if not tmdb_id:
            raise HTTPException(status_code=404, detail="无法获取TMDB ID，请直接提供tmdb_id")

        # 获取TMDB适配器
        tmdb_adapter = await media_identify_service._get_tmdb_adapter(db)

        # 获取元数据
        if request.media_type == "movie":
            tmdb_data = await tmdb_adapter.get_movie_details(tmdb_id)
        else:
            tmdb_data = await tmdb_adapter.get_tv_details(tmdb_id)

        if not tmdb_data:
            raise HTTPException(status_code=404, detail="TMDB数据获取失败")

        # 创建或获取统一资源
        from app.models.unified_movie import UnifiedMovie
        from app.models.unified_tv_series import UnifiedTVSeries
        from app.constants import UNIFIED_TABLE_MOVIES, UNIFIED_TABLE_TV

        if request.media_type == "movie":
            unified_table = UNIFIED_TABLE_MOVIES
            existing = await db.execute(
                select(UnifiedMovie).where(UnifiedMovie.tmdb_id == tmdb_id)
            )
            unified = existing.scalar_one_or_none()
            if not unified:
                unified = UnifiedMovie(tmdb_id=tmdb_id, **{
                    k: v for k, v in tmdb_data.items()
                    if k != "tmdb_id" and hasattr(UnifiedMovie, k)
                })
                db.add(unified)
                await db.flush()
        else:
            unified_table = UNIFIED_TABLE_TV
            existing = await db.execute(
                select(UnifiedTVSeries).where(UnifiedTVSeries.tmdb_id == tmdb_id)
            )
            unified = existing.scalar_one_or_none()
            if not unified:
                # 将日期字符串转换为 date 对象（兼容 SQLite）
                for date_field in ("first_air_date", "last_air_date"):
                    val = tmdb_data.get(date_field)
                    if isinstance(val, str):
                        try:
                            tmdb_data[date_field] = datetime.strptime(val, "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            tmdb_data[date_field] = None
                unified = UnifiedTVSeries(tmdb_id=tmdb_id, **{
                    k: v for k, v in tmdb_data.items()
                    if k != "tmdb_id" and hasattr(UnifiedTVSeries, k)
                })
                db.add(unified)
                await db.flush()

        # 更新目录关联
        directory.unified_table_name = unified_table
        directory.unified_resource_id = unified.id
        if hasattr(unified, 'title') and unified.title:
            directory.series_name = unified.title

        # 同时更新该目录下所有视频文件的关联
        from app.models.media_file import MediaFile as MF
        stmt = select(MF).where(MF.media_directory_id == directory_id)
        files_result = await db.execute(stmt)
        files = files_result.scalars().all()
        for f in files:
            f.unified_table_name = unified_table
            f.unified_resource_id = unified.id
            if f.media_type in ("unknown", None):
                f.media_type = request.media_type

        await db.commit()

        return {
            "success": True,
            "unified_resource_id": unified.id,
            "unified_table_name": unified_table,
            "title": getattr(unified, 'title', None),
            "message": f"成功关联到 {getattr(unified, 'title', tmdb_id)}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"关联目录失败: {directory_id}")
        raise HTTPException(status_code=500, detail=f"关联失败: {str(e)}")


@router.delete("/{directory_id}")
async def delete_directory(
    directory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除目录记录"""
    success = await MediaDirectoryService.delete_by_id(db, directory_id)
    if not success:
        raise HTTPException(status_code=404, detail="目录不存在")

    return {"message": "目录已删除"}
