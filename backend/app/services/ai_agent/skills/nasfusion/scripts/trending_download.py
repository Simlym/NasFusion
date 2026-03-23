# -*- coding: utf-8 -*-
"""
榜单下载 Skill

场景：「下载豆瓣热门电影第一名」
编排：trending_query → 取指定名次 → resource_search → 选最优 → download_create
"""
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_agent.skills.nasfusion.scripts.base import BaseSkill
from app.services.ai_agent.tool_registry import register_tool

_COLLECTION_MEDIA_TYPE = {
    "douban_hot_movie": "movie",
    "douban_top250_movie": "movie",
    "douban_hot_tv": "tv",
    "tmdb_popular_movie": "movie",
    "tmdb_top_rated_movie": "movie",
    "tmdb_popular_tv": "tv",
}


def _select_best(resources: List[Dict]) -> Dict:
    """免费优先，再按做种数降序"""
    if not resources:
        return {}
    free = [r for r in resources if r.get("is_free")]
    pool = free if free else resources
    return max(pool, key=lambda r: r.get("seeders", 0))


@register_tool
class TrendingDownloadSkill(BaseSkill):
    """榜单下载：从指定榜单取指定名次并自动下载"""

    name = "trending_download"
    description = (
        "从榜单下载：查询指定榜单后，自动搜索并下载指定名次的影片。"
        "适用场景：「下载豆瓣热门电影第一名」「把 TMDB 评分最高电影下载下来」「下载豆瓣 Top250 第5名」。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "collection_type": {
                "type": "string",
                "description": "榜单类型",
                "enum": [
                    "douban_hot_movie", "douban_top250_movie", "douban_hot_tv",
                    "tmdb_popular_movie", "tmdb_top_rated_movie", "tmdb_popular_tv",
                ],
                "default": "douban_hot_movie",
            },
            "rank": {
                "type": "integer",
                "description": "榜单名次（从 1 开始，默认第 1 名）",
                "default": 1,
            },
            "resolution": {
                "type": "string",
                "description": "期望分辨率（不指定则不限）",
                "enum": ["2160p", "1080p", "720p", "480p"],
            },
            "prefer_free": {
                "type": "boolean",
                "description": "是否优先选择免费资源",
                "default": True,
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
        collection_type = arguments.get("collection_type", "douban_hot_movie")
        rank = max(1, arguments.get("rank", 1))
        resolution = arguments.get("resolution")
        prefer_free = arguments.get("prefer_free", True)
        steps = []

        from app.services.ai_agent.tools.query import TrendingQueryTool

        trending_result = await TrendingQueryTool.execute(db, user_id, {
            "collection_type": collection_type, "limit": rank,
        })
        steps.append({"step": "trending_query", "collection": collection_type})

        items = trending_result.get("items", [])
        if not items or len(items) < rank:
            return {
                "success": False,
                "error": f"榜单「{collection_type}」数据不足，未找到第 {rank} 名，请先同步榜单数据",
                "steps": steps,
            }

        target = items[rank - 1]
        title = target.get("title", "")
        media_type = _COLLECTION_MEDIA_TYPE.get(collection_type, "movie")
        steps.append({"step": "pick_item", "rank": rank, "title": title})

        from app.services.ai_agent.tools.resource import ResourceSearchTool

        search_args: Dict[str, Any] = {
            "keyword": title, "media_type": media_type, "limit": 20,
        }
        if resolution:
            search_args["resolution"] = resolution
        if prefer_free:
            search_args["promotion"] = "free"

        search_result = await ResourceSearchTool.execute(db, user_id, search_args)
        resources = search_result.get("resources", [])

        if prefer_free and not resources:
            search_args.pop("promotion", None)
            search_result = await ResourceSearchTool.execute(db, user_id, search_args)
            resources = search_result.get("resources", [])

        steps.append({"step": "search_resource", "found": len(resources)})

        if not resources:
            return {
                "success": False,
                "error": f"榜单第 {rank} 名《{title}》在 PT 站点暂无资源，建议同步后重试",
                "trending_item": target,
                "steps": steps,
            }

        best = _select_best(resources)
        steps.append({
            "step": "select_best",
            "resource_id": best.get("id"),
            "title": best.get("title"),
            "is_free": best.get("is_free"),
        })

        from app.services.ai_agent.tools.download import DownloadCreateTool

        dl_result = await DownloadCreateTool.execute(db, user_id, {
            "resource_id": best["id"], "priority": "normal",
        })
        steps.append({"step": "create_download", "success": dl_result.get("success")})

        if not dl_result.get("success"):
            return {
                "success": False,
                "error": dl_result.get("error", "创建下载任务失败"),
                "trending_item": target,
                "selected_resource": best,
                "steps": steps,
            }

        return {
            "success": True,
            "message": f"榜单第{rank}名《{title}》{dl_result['message']}",
            "trending_item": {
                "rank": rank, "title": title,
                "rating": target.get("rating"),
                "overview": target.get("overview"),
            },
            "resource": {
                "title": best.get("title"),
                "resolution": best.get("resolution"),
                "size": best.get("size_str"),
                "is_free": best.get("is_free"),
                "seeders": best.get("seeders"),
            },
            "download_task": dl_result.get("download_task"),
            "steps": steps,
        }
