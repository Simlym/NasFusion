# -*- coding: utf-8 -*-
"""
智能下载 Skill

场景：「下载《流浪地球2》1080p 免费资源」
编排：resource_search → 选最优资源 → download_create
"""
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_agent.skills.scripts.base import BaseSkill
from app.services.ai_agent.tool_registry import register_tool


def _select_best(resources: List[Dict]) -> Dict:
    """免费优先，再按做种数降序"""
    if not resources:
        return {}
    free = [r for r in resources if r.get("is_free")]
    pool = free if free else resources
    return max(pool, key=lambda r: r.get("seeders", 0))


@register_tool
class SmartDownloadSkill(BaseSkill):
    """智能下载：搜索最优 PT 资源并创建下载任务"""

    name = "smart_download"
    description = (
        "一键智能下载：自动搜索 PT 资源并下载最优匹配项。"
        "优先选择免费（free/2x_free）资源，同等条件下优先选择做种人数最多的资源。"
        "适用场景：「下载《流浪地球2》1080p」「帮我下载最新的阿凡达」「下载免费的黑镜第6季」。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "影视名称"},
            "media_type": {
                "type": "string",
                "description": "媒体类型：movie / tv",
                "enum": ["movie", "tv"],
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
        "required": ["title"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        title = arguments.get("title", "")
        media_type = arguments.get("media_type")
        resolution = arguments.get("resolution")
        prefer_free = arguments.get("prefer_free", True)
        steps = []

        from app.services.ai_agent.tools.resource import ResourceSearchTool

        search_args: Dict[str, Any] = {"keyword": title, "limit": 20}
        if media_type:
            search_args["media_type"] = media_type
        if resolution:
            search_args["resolution"] = resolution
        if prefer_free:
            search_args["promotion"] = "free"

        search_result = await ResourceSearchTool.execute(db, user_id, search_args)
        resources = search_result.get("resources", [])
        steps.append({"step": "search_resource", "found": len(resources)})

        # 无免费资源时放开限免重试
        if prefer_free and not resources:
            search_args.pop("promotion", None)
            search_result = await ResourceSearchTool.execute(db, user_id, search_args)
            resources = search_result.get("resources", [])
            steps.append({"step": "search_no_promo", "found": len(resources)})

        if not resources:
            return {
                "success": False,
                "error": f"未找到「{title}」的资源，建议先同步 PT 站点后重试",
                "steps": steps,
            }

        best = _select_best(resources)
        steps.append({
            "step": "select_best",
            "resource_id": best.get("id"),
            "title": best.get("title"),
            "is_free": best.get("is_free"),
            "seeders": best.get("seeders"),
            "size": best.get("size_str"),
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
                "selected_resource": best,
                "steps": steps,
            }

        return {
            "success": True,
            "message": dl_result["message"],
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
