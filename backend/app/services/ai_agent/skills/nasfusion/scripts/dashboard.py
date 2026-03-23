# -*- coding: utf-8 -*-
"""
系统总览 Skill

场景：「系统现在怎么样」「有什么在下载吗」
编排：system_status + download_status + subscription_list（聚合三个工具结果）
"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_agent.skills.nasfusion.scripts.base import BaseSkill
from app.services.ai_agent.tool_registry import register_tool


@register_tool
class DashboardSkill(BaseSkill):
    """系统总览：一次返回下载、订阅和系统健康状况的综合摘要"""

    name = "dashboard"
    description = (
        "系统总览：一次返回下载状态、活跃订阅和系统健康状况的综合摘要。"
        "适用场景：「系统现在怎么样」「给我看看总体情况」「有什么在下载吗」「我的订阅都正常吗」。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "description": "聚焦模块（默认全部）：downloads / subscriptions / system / all",
                "enum": ["downloads", "subscriptions", "system", "all"],
                "default": "all",
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
        focus = arguments.get("focus", "all")

        from app.services.ai_agent.tools.query import SystemStatusTool, DownloadStatusTool
        from app.services.ai_agent.tools.subscription import SubscriptionListTool

        result: Dict[str, Any] = {"success": True}
        sections = []

        if focus in ("all", "system"):
            sys_result = await SystemStatusTool.execute(db, user_id, {"include": ["all"]})
            result["system"] = sys_result.get("status", {})
            sections.append(f"系统{'正常' if sys_result.get('success') else '异常'}")

        if focus in ("all", "downloads"):
            dl_result = await DownloadStatusTool.execute(db, user_id, {"limit": 10})
            result["downloads"] = {
                "summary": dl_result.get("summary", {}),
                "tasks": dl_result.get("tasks", []),
            }
            s = dl_result.get("summary", {})
            sections.append(f"下载中{s.get('downloading', 0)}个（共{s.get('total', 0)}个任务）")

        if focus in ("all", "subscriptions"):
            sub_result = await SubscriptionListTool.execute(db, user_id, {
                "status": "active", "limit": 20,
            })
            result["subscriptions"] = {
                "summary": sub_result.get("summary", {}),
                "list": sub_result.get("subscriptions", []),
            }
            s = sub_result.get("summary", {})
            sections.append(f"活跃订阅{s.get('active', 0)}个")

        result["message"] = "，".join(sections) if sections else "暂无数据"
        return result
