# -*- coding: utf-8 -*-
"""
同步工具

PT站点资源同步
"""
import asyncio
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_PT_SYNC
from app.constants.task import TASK_TYPE_PT_RESOURCE_SYNC
from app.models import PTSite
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class PTSyncTool(BaseTool):
    """PT站点同步工具"""

    name = AGENT_TOOL_PT_SYNC
    description = """同步PT站点资源。可以触发指定站点或所有站点的资源同步。
    同步会在后台执行，可能需要几分钟时间。"""

    parameters = {
        "type": "object",
        "properties": {
            "site_name": {
                "type": "string",
                "description": "站点名称（不传则同步所有站点）",
            },
            "pages": {
                "type": "integer",
                "description": "同步页数",
                "default": 3,
            },
            "sync_mode": {
                "type": "string",
                "description": "同步模式",
                "enum": ["normal", "adult"],
                "default": "normal",
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
        """执行PT站点同步"""
        site_name = arguments.get("site_name")
        pages = min(arguments.get("pages", 3), 10)
        sync_mode = arguments.get("sync_mode", "normal")

        # 查找站点
        if site_name:
            site_result = await db.execute(
                select(PTSite).where(PTSite.name.ilike(f"%{site_name}%"))
            )
            site = site_result.scalar_one_or_none()

            if not site:
                return {
                    "success": False,
                    "error": f"未找到站点「{site_name}」",
                }

            sites = [site]
        else:
            # 获取所有活跃站点
            sites_result = await db.execute(
                select(PTSite).where(PTSite.status == "active")
            )
            sites = sites_result.scalars().all()

            if not sites:
                return {
                    "success": False,
                    "error": "没有活跃的PT站点",
                }

        # 触发同步任务
        from app.services.task.scheduler_manager import scheduler_manager

        triggered_sites = []
        for site in sites:
            try:
                asyncio.create_task(
                    scheduler_manager.trigger_task(
                        task_type=TASK_TYPE_PT_RESOURCE_SYNC,
                        params={
                            "site_id": site.id,
                            "pages": pages,
                            "sync_mode": sync_mode,
                        },
                    )
                )
                triggered_sites.append({
                    "id": site.id,
                    "name": site.name,
                })
            except Exception as e:
                pass  # 忽略单个站点的错误

        if not triggered_sites:
            return {
                "success": False,
                "error": "同步任务启动失败",
            }

        return {
            "success": True,
            "message": f"已触发{len(triggered_sites)}个站点的同步任务，同步将在后台执行",
            "sites": triggered_sites,
            "params": {
                "pages": pages,
                "sync_mode": sync_mode,
            },
        }
