# -*- coding: utf-8 -*-
"""
追剧订阅 Skill 执行逻辑

技能描述（description、parameters）见同目录的 subscribe_tv.yaml。
此文件只负责编排工具调用，完成「搜索资源 → 创建订阅」两步流程。
"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_agent.skills.base import BaseSkill
from app.services.ai_agent.tool_registry import register_tool


@register_tool
class SubscribeTVSkill(BaseSkill):
    """追剧订阅 Skill（元数据见 subscribe_tv.yaml）"""

    # name/description/parameters 从 subscribe_tv.yaml 加载，此处留空即可
    name = "subscribe_tv"

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

        # Step 1：搜索 PT 资源，确认有可用资源
        from app.services.ai_agent.tools.resource import ResourceSearchTool

        search_result = await ResourceSearchTool.execute(db, user_id, {
            "keyword": title,
            "media_type": "tv",
            "limit": 5,
        })
        steps.append({"step": "search_resource", "found": search_result.get("total", 0)})

        if not search_result.get("success") or search_result.get("total", 0) == 0:
            return {
                "success": False,
                "error": f"未在 PT 站点找到「{title}」的资源，请先同步 PT 资源后重试",
                "steps": steps,
            }

        # Step 2：创建订阅
        from app.services.ai_agent.tools.subscription import SubscriptionCreateTool

        sub_result = await SubscriptionCreateTool.execute(db, user_id, {
            "media_type": "tv",
            "title": title,
            "season": season,
            "quality_mode": quality_mode,
            "auto_download": True,
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
