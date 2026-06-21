# -*- coding: utf-8 -*-
"""
观看历史工具

查询当前用户在媒体服务器（Jellyfin/Emby/Plex）上的观看记录与统计，
可用于「最近看了什么」「看过哪些剧」以及为推荐提供依据。
"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_WATCH_HISTORY
from app.services.ai_agent.tool_registry import BaseTool, register_tool
from app.services.media_server.media_server_watch_history_service import (
    MediaServerWatchHistoryService,
)


@register_tool
class WatchHistoryTool(BaseTool):
    """观看历史查询工具"""

    name = AGENT_TOOL_WATCH_HISTORY
    description = (
        "查询当前用户的观看历史与统计。"
        "action=history 返回最近的观看记录（可按 media_type 过滤、is_completed 是否看完）；"
        "action=stats 返回观看总数、已看完数量、按类型分布。"
        "适合回答「我最近看了什么」或为推荐提供口味依据。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["history", "stats"],
                "default": "history",
            },
            "media_type": {
                "type": "string",
                "description": "媒体类型过滤（history 时使用）",
                "enum": ["movie", "tv", "music"],
            },
            "is_completed": {
                "type": "boolean",
                "description": "仅看完/未看完（history 时使用）",
            },
            "limit": {
                "type": "integer",
                "description": "返回记录数（history 时使用）",
                "default": 20,
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
        action = arguments.get("action", "history")

        if action == "stats":
            stats = await MediaServerWatchHistoryService.get_watch_statistics(
                db, user_id
            )
            return {
                "success": True,
                "message": (
                    f"共观看 {stats.get('total_count', 0)} 条，"
                    f"看完 {stats.get('completed_count', 0)} 条"
                ),
                "stats": stats,
            }

        # history
        limit = min(arguments.get("limit", 20), 100)
        filters: Dict[str, Any] = {}
        if arguments.get("media_type"):
            filters["media_type"] = arguments["media_type"]
        if arguments.get("is_completed") is not None:
            filters["is_completed"] = arguments["is_completed"]

        records, total = await MediaServerWatchHistoryService.get_user_watch_history(
            db, user_id, filters=filters or None, limit=limit, offset=0
        )

        history = []
        for r in records:
            history.append(
                {
                    "title": r.title,
                    "media_type": r.media_type,
                    "year": r.year,
                    "season_number": r.season_number,
                    "episode_number": r.episode_number,
                    "episode_title": r.episode_title,
                    "play_count": r.play_count,
                    "is_completed": r.is_completed,
                    "last_played_at": r.last_played_at.isoformat()
                    if r.last_played_at
                    else None,
                }
            )

        return {
            "success": True,
            "message": f"返回最近 {len(history)} 条观看记录（共 {total} 条）",
            "total": total,
            "history": history,
        }
