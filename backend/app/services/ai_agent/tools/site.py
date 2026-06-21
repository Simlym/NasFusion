# -*- coding: utf-8 -*-
"""
站点运维工具

测试站点连接、查询站点用户数据（上传/下载/分享率/魔力值等）
"""
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_SITE_MANAGE
from app.models import PTSite
from app.services.ai_agent.tool_registry import BaseTool, register_tool
from app.services.pt.pt_site_service import PTSiteService


@register_tool
class SiteManageTool(BaseTool):
    """PT 站点运维工具"""

    name = AGENT_TOOL_SITE_MANAGE
    description = (
        "PT 站点运维。支持三种操作："
        "list（列出所有站点及健康状态）、"
        "test（测试指定站点连接是否正常）、"
        "userdata（刷新并查询站点用户数据：上传量、下载量、分享率、魔力值等）。"
        "test 与 userdata 需要提供 site_id 或 site_name 之一。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["list", "test", "userdata"],
                "default": "list",
            },
            "site_id": {
                "type": "integer",
                "description": "站点 ID（test/userdata 时使用）",
            },
            "site_name": {
                "type": "string",
                "description": "站点名称（test/userdata 时使用，与 site_id 二选一）",
            },
        },
        "required": [],
    }

    @classmethod
    async def _resolve_site(
        cls,
        db: AsyncSession,
        arguments: Dict[str, Any],
    ):
        """根据 site_id 或 site_name 定位站点"""
        site_id = arguments.get("site_id")
        if site_id:
            return await PTSiteService.get_by_id(db, site_id)

        site_name = arguments.get("site_name")
        if site_name:
            result = await db.execute(
                select(PTSite).where(PTSite.name == site_name)
            )
            return result.scalar_one_or_none()

        return None

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        action = arguments.get("action", "list")

        if action == "list":
            result = await db.execute(select(PTSite))
            sites = result.scalars().all()
            return {
                "success": True,
                "message": f"共 {len(sites)} 个站点",
                "sites": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "domain": s.domain,
                        "status": s.status,
                        "health_status": s.health_status,
                        "health_check_at": s.health_check_at.isoformat()
                        if s.health_check_at
                        else None,
                    }
                    for s in sites
                ],
            }

        # test / userdata 都需要先定位站点
        site = await cls._resolve_site(db, arguments)
        if not site:
            return {
                "success": False,
                "error": "未找到站点，请提供有效的 site_id 或 site_name",
            }

        if action == "test":
            ok, msg = await PTSiteService.test_connection(db, site.id)
            return {
                "success": ok,
                "message": msg,
                "site": {"id": site.id, "name": site.name},
            }

        if action == "userdata":
            profile = await PTSiteService.refresh_user_profile(db, site.id)
            if profile is None:
                return {
                    "success": False,
                    "error": f"获取「{site.name}」用户数据失败，请检查站点连接与认证",
                }
            return {
                "success": True,
                "message": f"「{site.name}」用户数据已刷新",
                "site": {"id": site.id, "name": site.name},
                "user_profile": profile,
            }

        return {"success": False, "error": f"未知操作: {action}"}
