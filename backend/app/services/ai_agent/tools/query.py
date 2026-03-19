# -*- coding: utf-8 -*-
"""
查询工具

媒体库、榜单、系统状态查询
"""
from typing import Any, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import (
    AGENT_TOOL_MEDIA_QUERY,
    AGENT_TOOL_TRENDING_QUERY,
    AGENT_TOOL_SYSTEM_STATUS,
)
from app.models import (
    MediaFile,
    PTSite,
    PTResource,
    DownloadTask,
    Subscription,
    DownloaderConfig,
)
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class MediaQueryTool(BaseTool):
    """媒体库查询工具"""

    name = AGENT_TOOL_MEDIA_QUERY
    description = """查询本地媒体库中的内容。可以搜索电影、剧集，查看媒体库统计等。"""

    parameters = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词",
            },
            "media_type": {
                "type": "string",
                "description": "媒体类型",
                "enum": ["movie", "tv", "anime", "music"],
            },
            "organized": {
                "type": "boolean",
                "description": "是否已整理",
            },
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["search", "stats"],
                "default": "search",
            },
            "limit": {
                "type": "integer",
                "description": "结果数量",
                "default": 10,
            },
        },
        "required": [],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行媒体库查询"""
        action = arguments.get("action", "search")
        keyword = arguments.get("keyword")
        media_type = arguments.get("media_type")
        organized = arguments.get("organized")
        limit = min(arguments.get("limit", 10), 50)

        if action == "stats":
            # 统计信息
            total_query = select(func.count(MediaFile.id))
            total_result = await db.execute(total_query)
            total = total_result.scalar() or 0

            organized_query = select(func.count(MediaFile.id)).where(
                MediaFile.organized == True
            )
            organized_result = await db.execute(organized_query)
            organized_count = organized_result.scalar() or 0

            # 按类型统计
            type_stats = {}
            for mt in ["movie", "tv", "anime", "music"]:
                type_query = select(func.count(MediaFile.id)).where(
                    MediaFile.media_type == mt
                )
                type_result = await db.execute(type_query)
                type_stats[mt] = type_result.scalar() or 0

            return {
                "success": True,
                "message": f"媒体库共{total}个文件，已整理{organized_count}个",
                "stats": {
                    "total": total,
                    "organized": organized_count,
                    "unorganized": total - organized_count,
                    "by_type": type_stats,
                },
            }

        else:  # search
            query = select(MediaFile)

            if keyword:
                query = query.where(MediaFile.file_name.ilike(f"%{keyword}%"))

            if media_type:
                query = query.where(MediaFile.media_type == media_type)

            if organized is not None:
                query = query.where(MediaFile.organized == organized)

            query = query.order_by(
                MediaFile.episode_number.desc(),
                MediaFile.created_at.desc(),
            ).limit(limit)

            result = await db.execute(query)
            files = result.scalars().all()

            if not files:
                return {
                    "success": True,
                    "message": "未找到匹配的媒体文件",
                    "files": [],
                }

            file_list = []
            for f in files:
                file_list.append({
                    "id": f.id,
                    "file_name": f.file_name,
                    "media_type": f.media_type,
                    "file_size": f.file_size,
                    "organized": f.organized,
                    "status": f.status,
                    "season_number": f.season_number,
                    "episode_number": f.episode_number,
                    "episode_title": f.episode_title,
                })

            return {
                "success": True,
                "message": f"找到{len(file_list)}个媒体文件",
                "files": file_list,
            }


@register_tool
class TrendingQueryTool(BaseTool):
    """榜单查询工具"""

    name = AGENT_TOOL_TRENDING_QUERY
    description = """查询热门榜单。支持豆瓣热门、豆瓣Top250、TMDB热门等榜单。"""

    parameters = {
        "type": "object",
        "properties": {
            "collection_type": {
                "type": "string",
                "description": "榜单类型",
                "enum": [
                    "douban_hot_movie",
                    "douban_top250_movie",
                    "douban_hot_tv",
                    "tmdb_popular_movie",
                    "tmdb_top_rated_movie",
                    "tmdb_popular_tv",
                ],
            },
            "limit": {
                "type": "integer",
                "description": "结果数量",
                "default": 10,
            },
        },
        "required": [],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行榜单查询"""
        collection_type = arguments.get("collection_type", "douban_hot_movie")
        limit = min(arguments.get("limit", 10), 50)

        # 导入榜单模型
        from app.models.trending import TrendingCollection, TrendingItem

        # 查找榜单
        collection_result = await db.execute(
            select(TrendingCollection).where(
                TrendingCollection.collection_type == collection_type
            )
        )
        collection = collection_result.scalar_one_or_none()

        if not collection:
            return {
                "success": True,
                "message": f"榜单「{collection_type}」暂无数据，请先同步榜单",
                "items": [],
            }

        # 查询榜单项目
        items_result = await db.execute(
            select(TrendingItem)
            .where(TrendingItem.collection_id == collection.id)
            .order_by(TrendingItem.rank)
            .limit(limit)
        )
        items = items_result.scalars().all()

        if not items:
            return {
                "success": True,
                "message": "榜单暂无内容",
                "items": [],
            }

        # 格式化结果
        item_list = []
        for item in items:
            item_list.append({
                "rank": item.rank,
                "title": item.title,
                "original_title": item.original_title,
                "year": item.year,
                "rating": item.rating,
                "rating_count": item.rating_count,
                "genres": item.genres,
                "overview": item.overview[:100] if item.overview else None,
            })

        # 榜单类型显示名
        type_names = {
            "douban_hot_movie": "豆瓣热门电影",
            "douban_top250_movie": "豆瓣Top250",
            "douban_hot_tv": "豆瓣热门剧集",
            "tmdb_popular_movie": "TMDB热门电影",
            "tmdb_top_rated_movie": "TMDB高分电影",
            "tmdb_popular_tv": "TMDB热门剧集",
        }

        return {
            "success": True,
            "message": f"{type_names.get(collection_type, collection_type)} 榜单（前{len(item_list)}名）",
            "collection": {
                "name": collection.name,
                "type": collection.collection_type,
                "updated_at": collection.updated_at.isoformat() if collection.updated_at else None,
            },
            "items": item_list,
        }


@register_tool
class SystemStatusTool(BaseTool):
    """系统状态查询工具"""

    name = AGENT_TOOL_SYSTEM_STATUS
    description = """查询系统状态。包括PT站点状态、下载器状态、资源统计等。"""

    parameters = {
        "type": "object",
        "properties": {
            "include": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["sites", "downloaders", "resources", "tasks", "all"],
                },
                "description": "要包含的信息类型",
                "default": ["all"],
            },
        },
        "required": [],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行系统状态查询"""
        include = arguments.get("include", ["all"])
        include_all = "all" in include

        status = {}

        # PT站点状态
        if include_all or "sites" in include:
            sites_result = await db.execute(select(PTSite))
            sites = sites_result.scalars().all()

            site_status = []
            for site in sites:
                site_status.append({
                    "name": site.name,
                    "status": site.status,
                    "health_status": site.health_status,
                    "last_sync_at": site.last_sync_at.isoformat() if site.last_sync_at else None,
                })

            status["sites"] = {
                "total": len(sites),
                "healthy": len([s for s in sites if s.health_status == "healthy"]),
                "list": site_status,
            }

        # 下载器状态
        if include_all or "downloaders" in include:
            downloaders_result = await db.execute(select(DownloaderConfig))
            downloaders = downloaders_result.scalars().all()

            downloader_status = []
            for d in downloaders:
                downloader_status.append({
                    "name": d.name,
                    "type": d.downloader_type,
                    "status": d.status,
                    "is_default": d.is_default,
                })

            status["downloaders"] = {
                "total": len(downloaders),
                "online": len([d for d in downloaders if d.status == "online"]),
                "list": downloader_status,
            }

        # 资源统计
        if include_all or "resources" in include:
            resource_count = await db.execute(
                select(func.count(PTResource.id))
            )
            total_resources = resource_count.scalar() or 0

            free_count = await db.execute(
                select(func.count(PTResource.id)).where(PTResource.is_free == True)
            )
            free_resources = free_count.scalar() or 0

            status["resources"] = {
                "total": total_resources,
                "free": free_resources,
            }

        # 任务统计
        if include_all or "tasks" in include:
            # 下载任务
            download_tasks = await db.execute(
                select(func.count(DownloadTask.id))
            )
            total_downloads = download_tasks.scalar() or 0

            downloading = await db.execute(
                select(func.count(DownloadTask.id)).where(
                    DownloadTask.status == "downloading"
                )
            )
            downloading_count = downloading.scalar() or 0

            # 订阅
            subscriptions = await db.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.user_id == user_id
                )
            )
            total_subs = subscriptions.scalar() or 0

            active_subs = await db.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",
                )
            )
            active_sub_count = active_subs.scalar() or 0

            status["tasks"] = {
                "downloads": {
                    "total": total_downloads,
                    "downloading": downloading_count,
                },
                "subscriptions": {
                    "total": total_subs,
                    "active": active_sub_count,
                },
            }

        return {
            "success": True,
            "message": "系统状态正常",
            "status": status,
        }
