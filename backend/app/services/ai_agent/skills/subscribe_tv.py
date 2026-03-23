# -*- coding: utf-8 -*-
"""
追剧订阅 Skill

场景：「帮我追《黑镜》第7季」
编排：resource_search → subscription_create（TV）
"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_agent.skills.base import BaseSkill
from app.services.ai_agent.tool_registry import register_tool


@register_tool
class SubscribeTVSkill(BaseSkill):
    """追剧订阅：自动搜索 PT 资源后创建订阅，系统将自动下载新集"""

    name = "subscribe_tv"
    description = (
        "一键追剧：自动搜索 PT 资源后创建订阅，系统将自动下载新集。"
        "适用场景：「帮我追《黑镜》第7季」「订阅最新一季的《纸牌屋》」。"
        "注意：需要指定季数，且剧集须已在本地媒体库中识别过。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "剧集名称（中文或英文均可）"},
            "season": {"type": "integer", "description": "订阅季数（必须指定）"},
            "quality_mode": {
                "type": "string",
                "description": "质量模式：first_match（速度优先）/ best_match（质量优先）",
                "enum": ["first_match", "best_match"],
                "default": "best_match",
            },
        },
        "required": ["title", "season"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        title = arguments.get("title", "")
        season = arguments.get("season")
        quality_mode = arguments.get("quality_mode", "best_match")
        steps = []

        from app.services.ai_agent.tools.resource import ResourceSearchTool

        search_result = await ResourceSearchTool.execute(db, user_id, {
            "keyword": title, "media_type": "tv", "limit": 5,
        })
        steps.append({"step": "search_resource", "found": search_result.get("total", 0)})

        if not search_result.get("success") or search_result.get("total", 0) == 0:
            return {
                "success": False,
                "error": f"未在 PT 站点找到「{title}」的资源，请先同步 PT 资源后重试",
                "steps": steps,
            }

        from app.services.ai_agent.tools.subscription import SubscriptionCreateTool

        sub_result = await SubscriptionCreateTool.execute(db, user_id, {
            "media_type": "tv", "title": title, "season": season,
            "quality_mode": quality_mode, "auto_download": True,
        })
        steps.append({"step": "create_subscription", "success": sub_result.get("success")})

        if not sub_result.get("success"):
            return {
                "success": False,
                "error": sub_result.get("error", "创建订阅失败"),
                "steps": steps,
                "hint": "如剧集未在媒体库中，请先执行资源识别任务",
            }

        return {
            "success": True,
            "message": sub_result["message"],
            "subscription": sub_result.get("subscription"),
            "resource_count": search_result.get("total", 0),
            "steps": steps,
        }
