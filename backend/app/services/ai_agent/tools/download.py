# -*- coding: utf-8 -*-
"""
下载工具

创建和管理下载任务
"""
import asyncio
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_DOWNLOAD_CREATE, AGENT_TOOL_DOWNLOAD_MANAGE, AGENT_TOOL_DOWNLOAD_STATUS
from app.constants.task import TASK_TYPE_DOWNLOAD_CREATE
from app.models import PTResource, DownloadTask
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class DownloadCreateTool(BaseTool):
    """创建下载任务工具"""

    name = AGENT_TOOL_DOWNLOAD_CREATE
    description = """创建下载任务。根据PT资源ID创建下载任务，将资源添加到下载器中。
    需要先使用资源搜索工具找到资源ID。"""

    parameters = {
        "type": "object",
        "properties": {
            "resource_id": {
                "type": "integer",
                "description": "PT资源ID（从搜索结果中获取）",
            },
            "save_path": {
                "type": "string",
                "description": "保存路径（可选，使用默认路径）",
            },
            "priority": {
                "type": "string",
                "description": "下载优先级",
                "enum": ["high", "normal", "low"],
                "default": "normal",
            },
        },
        "required": ["resource_id"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行创建下载"""
        resource_id = arguments.get("resource_id")
        save_path = arguments.get("save_path")
        priority = arguments.get("priority", "normal")

        if not resource_id:
            return {
                "success": False,
                "error": "请提供资源ID",
            }

        # 查找资源
        resource_result = await db.execute(
            select(PTResource).where(PTResource.id == resource_id)
        )
        resource = resource_result.scalar_one_or_none()

        if not resource:
            return {
                "success": False,
                "error": f"资源ID {resource_id} 不存在",
            }

        # 检查是否已有下载任务
        existing_task = await db.execute(
            select(DownloadTask).where(DownloadTask.pt_resource_id == resource_id)
        )
        if existing_task.scalar_one_or_none():
            return {
                "success": False,
                "error": f"资源「{resource.title}」已有下载任务",
            }

        # 创建下载任务
        from app.services.download.download_task_service import DownloadTaskService
        from app.schemas.downloader import DownloadTaskCreate

        task_data = DownloadTaskCreate(
            pt_resource_id=resource_id,
            save_path=save_path,
            priority=1 if priority == "high" else (0 if priority == "normal" else -1),
        )

        download_task = await DownloadTaskService.create(db, task_data, user_id)

        # 异步触发下载
        from app.services.task.scheduler_manager import scheduler_manager
        asyncio.create_task(
            scheduler_manager.trigger_task(
                task_type=TASK_TYPE_DOWNLOAD_CREATE,
                params={"download_task_id": download_task.id},
            )
        )

        return {
            "success": True,
            "message": f"已创建下载任务：{resource.title}",
            "download_task": {
                "id": download_task.id,
                "resource_title": resource.title,
                "size": resource.size,
                "status": download_task.status,
            },
        }


@register_tool
class DownloadStatusTool(BaseTool):
    """下载状态查询工具"""

    name = AGENT_TOOL_DOWNLOAD_STATUS
    description = """查询下载任务状态。可以查看所有下载任务或特定任务的状态。"""

    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "integer",
                "description": "下载任务ID（可选，不传则查看全部）",
            },
            "status": {
                "type": "string",
                "description": "过滤状态",
                "enum": ["pending", "downloading", "seeding", "completed", "error", "paused"],
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
        """执行状态查询"""
        task_id = arguments.get("task_id")
        status = arguments.get("status")
        limit = min(arguments.get("limit", 10), 50)

        # 构建查询
        query = select(DownloadTask)

        if task_id:
            query = query.where(DownloadTask.id == task_id)

        if status:
            query = query.where(DownloadTask.status == status)

        query = query.order_by(DownloadTask.created_at.desc()).limit(limit)

        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return {
                "success": True,
                "message": "没有下载任务",
                "tasks": [],
            }

        # 格式化结果
        task_list = []
        for t in tasks:
            # 获取关联的资源信息
            resource = None
            if t.pt_resource_id:
                resource_result = await db.execute(
                    select(PTResource).where(PTResource.id == t.pt_resource_id)
                )
                resource = resource_result.scalar_one_or_none()

            task_list.append({
                "id": t.id,
                "title": resource.title if resource else t.name,
                "status": t.status,
                "progress": t.progress,
                "download_speed": t.download_speed,
                "upload_speed": t.upload_speed,
                "size": t.size,
                "downloaded": t.downloaded,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })

        # 统计信息
        downloading_count = len([t for t in task_list if t["status"] == "downloading"])
        completed_count = len([t for t in task_list if t["status"] == "completed"])
        seeding_count = len([t for t in task_list if t["status"] == "seeding"])

        return {
            "success": True,
            "message": f"共{len(task_list)}个任务：下载中{downloading_count}，做种{seeding_count}，已完成{completed_count}",
            "tasks": task_list,
            "summary": {
                "total": len(task_list),
                "downloading": downloading_count,
                "seeding": seeding_count,
                "completed": completed_count,
            },
        }


@register_tool
class DownloadManageTool(BaseTool):
    """下载任务管理工具"""

    name = AGENT_TOOL_DOWNLOAD_MANAGE
    description = """管理下载任务：暂停、恢复或删除。需要先通过下载状态工具获取任务ID。
    删除任务时可选择是否同时删除已下载的文件。"""

    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "integer",
                "description": "下载任务ID",
            },
            "action": {
                "type": "string",
                "description": "操作类型：pause（暂停）、resume（恢复）、delete（删除）",
                "enum": ["pause", "resume", "delete"],
            },
            "delete_files": {
                "type": "boolean",
                "description": "删除任务时是否同时删除已下载的文件（仅 action=delete 时有效，默认 false）",
                "default": False,
            },
        },
        "required": ["task_id", "action"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行下载任务管理"""
        task_id = arguments.get("task_id")
        action = arguments.get("action")
        delete_files = arguments.get("delete_files", False)

        from app.services.download.download_task_service import DownloadTaskService

        task = await DownloadTaskService.get_by_id(db, task_id)
        if not task:
            return {"success": False, "error": f"下载任务 ID={task_id} 不存在"}

        task_name = task.torrent_name or f"任务#{task_id}"

        if action == "pause":
            success = await DownloadTaskService.pause_task(db, task_id)
            if success:
                return {"success": True, "message": f"已暂停：{task_name}"}
            return {"success": False, "error": f"暂停失败，任务可能已处于暂停状态"}

        elif action == "resume":
            success = await DownloadTaskService.resume_task(db, task_id)
            if success:
                return {"success": True, "message": f"已恢复：{task_name}"}
            return {"success": False, "error": f"恢复失败，请检查下载器连接"}

        elif action == "delete":
            success = await DownloadTaskService.delete_task(db, task_id, delete_files=delete_files)
            if success:
                suffix = "（含文件）" if delete_files else "（保留文件）"
                return {"success": True, "message": f"已删除{suffix}：{task_name}"}
            return {"success": False, "error": "删除失败，请检查下载器连接"}

        return {"success": False, "error": f"未知操作: {action}"}
