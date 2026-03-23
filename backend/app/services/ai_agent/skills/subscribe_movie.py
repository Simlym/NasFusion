# -*- coding: utf-8 -*-
"""
电影订阅 Skill

场景：「订阅《复仇者联盟5》」
编排：resource_search → subscription_create（movie）
"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_agent.skills.base import BaseSkill
from app.services.ai_agent.tool_registry import register_tool


@register_tool
class SubscribeMovieSkill(BaseSkill):
    """电影订阅：确认 PT 站点有资源后创建订阅，系统将自动下载"""

    name = "subscribe_movie"
    description = (
        "一键订阅电影：确认 PT 站点有资源后创建订阅，系统将自动下载。"
        "适用场景：「订阅《复仇者联盟5》」「帮我自动下载《哪吒3》上映后的资源」。"
        "注意：电影须已在本地媒体库中识别过；若尚未识别，请先执行资源识别任务。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "电影名称（中文或英文均可）"},
            "tmdb_id": {"type": "integer", "description": "TMDB ID（可选，精确匹配时使用）"},
            "quality_mode": {
                "type": "string",
                "description": "质量模式：first_match（有资源即下载）/ best_match（等待最优资源）",
                "enum": ["first_match", "best_match"],
                "default": "best_match",
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
        tmdb_id = arguments.get("tmdb_id")
        quality_mode = arguments.get("quality_mode", "best_match")
        steps = []

        from app.services.ai_agent.tools.resource import ResourceSearchTool

        search_result = await ResourceSearchTool.execute(db, user_id, {
            "keyword": title, "media_type": "movie", "limit": 5,
        })
        steps.append({"step": "search_resource", "found": search_result.get("total", 0)})

        if not search_result.get("success") or search_result.get("total", 0) == 0:
            return {
                "success": False,
                "error": f"未在 PT 站点找到电影「{title}」的资源，请先同步 PT 资源后重试",
                "steps": steps,
            }

        from app.services.ai_agent.tools.subscription import SubscriptionCreateTool

        sub_args: Dict[str, Any] = {
            "media_type": "movie", "title": title,
            "quality_mode": quality_mode, "auto_download": True,
        }
        if tmdb_id:
            sub_args["tmdb_id"] = tmdb_id

        sub_result = await SubscriptionCreateTool.execute(db, user_id, sub_args)
        steps.append({"step": "create_subscription", "success": sub_result.get("success")})

        if not sub_result.get("success"):
            return {
                "success": False,
                "error": sub_result.get("error", "创建订阅失败"),
                "steps": steps,
                "hint": "如电影未在媒体库中，请先执行资源识别任务",
            }

        return {
            "success": True,
            "message": sub_result["message"],
            "subscription": sub_result.get("subscription"),
            "resource_count": search_result.get("total", 0),
            "steps": steps,
        }
