# -*- coding: utf-8 -*-
"""
订阅工具

管理剧集订阅
"""
from typing import Any, Dict

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import (
    AGENT_TOOL_SUBSCRIPTION_CREATE,
    AGENT_TOOL_SUBSCRIPTION_DELETE,
    AGENT_TOOL_SUBSCRIPTION_LIST,
    AGENT_TOOL_SUBSCRIPTION_UPDATE,
)
from app.constants.subscription import SUBSCRIPTION_STATUS_ACTIVE
from app.models import Subscription, UnifiedTVSeries, UnifiedMovie
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class SubscriptionCreateTool(BaseTool):
    """创建订阅工具"""

    name = AGENT_TOOL_SUBSCRIPTION_CREATE
    description = """创建剧集/电影订阅。可以订阅正在播出的剧集，系统会自动检查新资源并下载。
    支持设置订阅的季数和起始集数。"""

    parameters = {
        "type": "object",
        "properties": {
            "media_type": {
                "type": "string",
                "description": "媒体类型",
                "enum": ["movie", "tv"],
            },
            "title": {
                "type": "string",
                "description": "影视名称（用于搜索）",
            },
            "tmdb_id": {
                "type": "integer",
                "description": "TMDB ID（可选，更精确）",
            },
            "season": {
                "type": "integer",
                "description": "订阅的季数（电视剧必填）",
            },
            "start_episode": {
                "type": "integer",
                "description": "起始集数（默认从第1集开始）",
                "default": 1,
            },
            "quality_mode": {
                "type": "string",
                "description": "质量模式",
                "enum": ["first_match", "best_match"],
                "default": "first_match",
            },
            "auto_download": {
                "type": "boolean",
                "description": "是否自动下载",
                "default": True,
            },
        },
        "required": ["media_type", "title"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行创建订阅"""
        media_type = arguments.get("media_type")
        title = arguments.get("title", "")
        tmdb_id = arguments.get("tmdb_id")
        season = arguments.get("season")
        start_episode = arguments.get("start_episode", 1)
        quality_mode = arguments.get("quality_mode", "first_match")
        auto_download = arguments.get("auto_download", True)

        if not title and not tmdb_id:
            return {
                "success": False,
                "error": "请提供影视名称或TMDB ID",
            }

        # 查找媒体
        media = None
        if media_type == "tv":
            query = select(UnifiedTVSeries)
            if tmdb_id:
                query = query.where(UnifiedTVSeries.tmdb_id == tmdb_id)
            else:
                query = query.where(
                    or_(
                        UnifiedTVSeries.title.ilike(f"%{title}%"),
                        UnifiedTVSeries.original_title.ilike(f"%{title}%"),
                    )
                ).limit(1)

            result = await db.execute(query)
            media = result.scalar_one_or_none()

            if not media:
                return {
                    "success": False,
                    "error": f"未找到剧集「{title}」，请确认名称或提供TMDB ID",
                }

            # 电视剧需要季数
            if not season:
                return {
                    "success": False,
                    "error": "订阅电视剧需要指定季数",
                }

        else:  # movie
            query = select(UnifiedMovie)
            if tmdb_id:
                query = query.where(UnifiedMovie.tmdb_id == tmdb_id)
            else:
                query = query.where(
                    or_(
                        UnifiedMovie.title.ilike(f"%{title}%"),
                        UnifiedMovie.original_title.ilike(f"%{title}%"),
                    )
                ).limit(1)

            result = await db.execute(query)
            media = result.scalar_one_or_none()

            if not media:
                return {
                    "success": False,
                    "error": f"未找到电影「{title}」，请确认名称或提供TMDB ID",
                }

        # 检查是否已有订阅
        existing_query = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == SUBSCRIPTION_STATUS_ACTIVE,
        )
        if media_type == "tv":
            existing_query = existing_query.where(
                Subscription.unified_tv_id == media.id,
                Subscription.current_season == season,
            )
        else:
            existing_query = existing_query.where(
                Subscription.unified_movie_id == media.id,
            )

        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return {
                "success": False,
                "error": f"已存在「{media.title}」的活跃订阅",
            }

        # 创建订阅
        from app.services.subscription.subscription_service import SubscriptionService
        from app.schemas.subscription import SubscriptionCreate

        sub_data = SubscriptionCreate(
            media_type=media_type,
            unified_tv_id=media.id if media_type == "tv" else None,
            unified_movie_id=media.id if media_type == "movie" else None,
            title=media.title,
            original_title=media.original_title,
            year=media.first_air_year if media_type == "tv" else media.year,
            tmdb_id=media.tmdb_id,
            douban_id=media.douban_id,
            current_season=season if media_type == "tv" else None,
            start_episode=start_episode if media_type == "tv" else None,
            quality_mode=quality_mode,
            auto_download=auto_download,
            poster_url=media.poster_url,
        )

        subscription = await SubscriptionService.create(db, user_id, sub_data)

        return {
            "success": True,
            "message": f"已创建订阅：{media.title}" + (
                f" 第{season}季（从第{start_episode}集开始）" if media_type == "tv" else ""
            ),
            "subscription": {
                "id": subscription.id,
                "title": subscription.title,
                "media_type": subscription.media_type,
                "season": subscription.current_season,
                "start_episode": subscription.start_episode,
                "auto_download": subscription.auto_download,
                "status": subscription.status,
            },
        }


@register_tool
class SubscriptionListTool(BaseTool):
    """订阅列表工具"""

    name = AGENT_TOOL_SUBSCRIPTION_LIST
    description = """查看订阅列表。可以查看所有订阅或按状态筛选。"""

    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "订阅状态筛选",
                "enum": ["active", "paused", "completed", "cancelled"],
            },
            "media_type": {
                "type": "string",
                "description": "媒体类型筛选",
                "enum": ["movie", "tv"],
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
        """执行订阅列表查询"""
        status = arguments.get("status")
        media_type = arguments.get("media_type")
        limit = min(arguments.get("limit", 10), 50)

        # 构建查询
        query = select(Subscription).where(Subscription.user_id == user_id)

        if status:
            query = query.where(Subscription.status == status)

        if media_type:
            query = query.where(Subscription.media_type == media_type)

        query = query.order_by(Subscription.created_at.desc()).limit(limit)

        result = await db.execute(query)
        subscriptions = result.scalars().all()

        if not subscriptions:
            return {
                "success": True,
                "message": "没有订阅",
                "subscriptions": [],
            }

        # 格式化结果
        sub_list = []
        for s in subscriptions:
            sub_list.append({
                "id": s.id,
                "title": s.title,
                "media_type": s.media_type,
                "status": s.status,
                "season": s.current_season,
                "current_episode": s.current_episode,
                "total_episodes": s.total_episodes,
                "auto_download": s.auto_download,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

        # 统计
        active_count = len([s for s in sub_list if s["status"] == "active"])
        completed_count = len([s for s in sub_list if s["status"] == "completed"])

        return {
            "success": True,
            "message": f"共{len(sub_list)}个订阅：活跃{active_count}，已完成{completed_count}",
            "subscriptions": sub_list,
            "summary": {
                "total": len(sub_list),
                "active": active_count,
                "completed": completed_count,
            },
        }


@register_tool
class SubscriptionUpdateTool(BaseTool):
    """修改订阅工具"""

    name = AGENT_TOOL_SUBSCRIPTION_UPDATE
    description = """修改已有订阅的设置。可以开启/关闭自动下载、暂停/恢复订阅、
    修改质量偏好等。需要先通过订阅列表工具获取订阅ID。"""

    parameters = {
        "type": "object",
        "properties": {
            "subscription_id": {
                "type": "integer",
                "description": "订阅ID（通过订阅列表获取）",
            },
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["enable_auto_download", "disable_auto_download", "pause", "resume", "update"],
            },
            "auto_download": {
                "type": "boolean",
                "description": "是否自动下载（action=update时使用）",
            },
            "quality_mode": {
                "type": "string",
                "description": "质量模式（action=update时使用）",
                "enum": ["first_match", "best_match"],
            },
        },
        "required": ["subscription_id", "action"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行修改订阅"""
        subscription_id = arguments.get("subscription_id")
        action = arguments.get("action")

        from app.services.subscription.subscription_service import SubscriptionService

        # 验证订阅属于该用户
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return {"success": False, "error": f"订阅 ID={subscription_id} 不存在"}
        if subscription.user_id != user_id:
            return {"success": False, "error": "无权限操作此订阅"}

        if action == "pause":
            result = await SubscriptionService.pause_subscription(db, subscription_id)
            return {
                "success": True,
                "message": f"订阅「{result.title}」已暂停",
                "subscription": {"id": result.id, "title": result.title, "status": result.status},
            }

        elif action == "resume":
            result = await SubscriptionService.resume_subscription(db, subscription_id)
            return {
                "success": True,
                "message": f"订阅「{result.title}」已恢复",
                "subscription": {"id": result.id, "title": result.title, "status": result.status},
            }

        elif action in ("enable_auto_download", "disable_auto_download", "update"):
            from app.schemas.subscription import SubscriptionUpdateSchema

            update_dict: Dict[str, Any] = {}

            if action == "enable_auto_download":
                update_dict["auto_download"] = True
            elif action == "disable_auto_download":
                update_dict["auto_download"] = False
            else:
                if "auto_download" in arguments:
                    update_dict["auto_download"] = arguments["auto_download"]
                if "quality_mode" in arguments:
                    update_dict["quality_mode"] = arguments["quality_mode"]

            if not update_dict:
                return {"success": False, "error": "未提供任何需要更新的字段"}

            update_data = SubscriptionUpdateSchema(**update_dict)
            result = await SubscriptionService.update_subscription(db, subscription_id, update_data)

            changed = ", ".join(
                f"{k}={'开启' if v is True else ('关闭' if v is False else v)}"
                for k, v in update_dict.items()
            )
            return {
                "success": True,
                "message": f"订阅「{result.title}」已更新：{changed}",
                "subscription": {
                    "id": result.id,
                    "title": result.title,
                    "auto_download": result.auto_download,
                    "status": result.status,
                },
            }

        return {"success": False, "error": f"未知操作: {action}"}


@register_tool
class SubscriptionDeleteTool(BaseTool):
    """删除订阅工具"""

    name = AGENT_TOOL_SUBSCRIPTION_DELETE
    description = """删除指定订阅。删除后无法恢复，已下载的文件不受影响。
    需要先通过订阅列表工具获取订阅ID进行确认。"""

    parameters = {
        "type": "object",
        "properties": {
            "subscription_id": {
                "type": "integer",
                "description": "订阅ID（通过订阅列表获取）",
            },
            "confirmed": {
                "type": "boolean",
                "description": "用户已确认删除（必须为 true 才会执行删除）",
            },
        },
        "required": ["subscription_id", "confirmed"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行删除订阅"""
        subscription_id = arguments.get("subscription_id")
        confirmed = arguments.get("confirmed", False)

        if not confirmed:
            return {
                "success": False,
                "error": "删除操作需要用户确认，请明确告知要删除该订阅",
            }

        from app.services.subscription.subscription_service import SubscriptionService

        # 先获取订阅信息用于回显
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return {"success": False, "error": f"订阅 ID={subscription_id} 不存在"}
        if subscription.user_id != user_id:
            return {"success": False, "error": "无权限操作此订阅"}

        title = subscription.title
        success = await SubscriptionService.delete_subscription(db, subscription_id)

        if success:
            return {
                "success": True,
                "message": f"订阅「{title}」已删除",
            }
        return {"success": False, "error": "删除失败，请稍后重试"}
