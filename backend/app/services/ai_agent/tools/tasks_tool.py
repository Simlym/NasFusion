# -*- coding: utf-8 -*-
"""
任务调度管理工具

查看和触发后台任务
"""
import asyncio
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_TASK_MANAGE
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class TaskManageTool(BaseTool):
    """任务调度管理工具"""

    name = AGENT_TOOL_TASK_MANAGE
    description = """查看和管理系统后台任务。可以列出所有调度任务及其状态、
    查看近期任务执行历史，或立即手动触发某个调度任务（如PT同步、订阅检查等）。"""

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型：list（列出任务）、history（执行历史）、trigger（立即触发）",
                "enum": ["list", "history", "trigger"],
            },
            "task_id": {
                "type": "integer",
                "description": "任务ID（action=trigger 时必填）",
            },
            "limit": {
                "type": "integer",
                "description": "结果数量（默认10）",
                "default": 10,
            },
            "task_type": {
                "type": "string",
                "description": "按任务类型过滤（action=list/history 时可选）",
            },
        },
        "required": ["action"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行任务管理操作"""
        action = arguments.get("action")
        task_id = arguments.get("task_id")
        limit = min(arguments.get("limit", 10), 50)
        task_type = arguments.get("task_type")

        if action == "list":
            return await cls._list_tasks(db, limit, task_type)
        elif action == "history":
            return await cls._task_history(db, limit, task_type)
        elif action == "trigger":
            if not task_id:
                return {"success": False, "error": "触发任务需要提供 task_id"}
            return await cls._trigger_task(db, task_id)

        return {"success": False, "error": f"未知操作: {action}"}

    @classmethod
    async def _list_tasks(
        cls, db: AsyncSession, limit: int, task_type: str | None
    ) -> Dict[str, Any]:
        """列出调度任务"""
        from app.services.task.scheduled_task_service import ScheduledTaskService

        tasks, total = await ScheduledTaskService.get_all(
            db, limit=limit, task_type=task_type
        )

        if not tasks:
            return {"success": True, "message": "没有调度任务", "tasks": [], "total": 0}

        task_list = []
        for t in tasks:
            next_run = t.next_run_at.strftime("%m-%d %H:%M") if t.next_run_at else "未计划"
            last_run = t.last_run_at.strftime("%m-%d %H:%M") if t.last_run_at else "从未执行"
            task_list.append({
                "id": t.id,
                "name": t.task_name,
                "type": t.task_type,
                "enabled": t.enabled,
                "last_run": last_run,
                "last_status": t.last_run_status or "未执行",
                "next_run": next_run,
                "total_runs": t.total_runs,
                "success_runs": t.success_runs,
                "failed_runs": t.failed_runs,
            })

        enabled_count = sum(1 for t in task_list if t["enabled"])
        return {
            "success": True,
            "message": f"共{total}个任务，已启用{enabled_count}个",
            "tasks": task_list,
            "total": total,
        }

    @classmethod
    async def _task_history(
        cls, db: AsyncSession, limit: int, task_type: str | None
    ) -> Dict[str, Any]:
        """查看执行历史"""
        from app.services.task.task_execution_service import TaskExecutionService

        executions, total = await TaskExecutionService.get_all(
            db, limit=limit, task_type=task_type
        )

        if not executions:
            return {"success": True, "message": "没有执行记录", "history": [], "total": 0}

        history = []
        for e in executions:
            started = e.started_at.strftime("%m-%d %H:%M:%S") if e.started_at else "-"
            duration = f"{e.execution_time}秒" if e.execution_time else "-"
            history.append({
                "id": e.id,
                "name": e.task_name,
                "type": e.task_type,
                "status": e.status,
                "started_at": started,
                "duration": duration,
                "error": e.error_message if e.status == "failed" else None,
            })

        failed = sum(1 for h in history if h["status"] == "failed")
        success = sum(1 for h in history if h["status"] == "completed")
        return {
            "success": True,
            "message": f"最近{len(history)}次执行：成功{success}次，失败{failed}次",
            "history": history,
            "total": total,
        }

    @classmethod
    async def _trigger_task(cls, db: AsyncSession, task_id: int) -> Dict[str, Any]:
        """立即触发任务"""
        from app.services.task.scheduler_manager import scheduler_manager
        from app.services.task.scheduled_task_service import ScheduledTaskService

        task = await ScheduledTaskService.get_by_id(db, task_id)
        if not task:
            return {"success": False, "error": f"任务 ID={task_id} 不存在"}

        if not task.enabled:
            return {"success": False, "error": f"任务「{task.task_name}」已禁用，无法触发"}

        execution_id = await scheduler_manager.run_task_now(task_id)

        return {
            "success": True,
            "message": f"已触发任务「{task.task_name}」，在后台执行中",
            "execution_id": execution_id,
            "task_name": task.task_name,
            "task_type": task.task_type,
        }
