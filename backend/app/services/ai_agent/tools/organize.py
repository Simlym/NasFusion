# -*- coding: utf-8 -*-
"""
媒体整理工具

将已扫描但未整理的媒体文件按规则整理（重命名/移动/硬链接）到媒体库目录。
默认 dry_run 预览，避免误操作；确认后才真正落盘。
"""
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_ORGANIZE_MEDIA
from app.models import MediaFile
from app.services.ai_agent.tool_registry import BaseTool, register_tool
from app.services.mediafile.media_organizer_service import MediaOrganizerService


@register_tool
class OrganizeMediaTool(BaseTool):
    """媒体整理工具"""

    name = AGENT_TOOL_ORGANIZE_MEDIA
    description = (
        "整理媒体文件：按规则把文件重命名并移动/硬链接到媒体库目录。"
        "可指定 media_file_ids，或不指定时自动整理所有「已识别但未整理」的文件。"
        "默认 dry_run=true 仅预览不实际移动文件；确认无误后再用 dry_run=false 执行。"
        "涉及实际移动文件的操作（dry_run=false）请先向用户确认。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "media_file_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "要整理的媒体文件 ID 列表；留空则整理所有已识别但未整理的文件",
            },
            "dry_run": {
                "type": "boolean",
                "description": "是否仅预览（不实际移动文件）",
                "default": True,
            },
            "force": {
                "type": "boolean",
                "description": "强制重新整理（忽略已整理状态）",
                "default": False,
            },
            "limit": {
                "type": "integer",
                "description": "自动模式下最多整理的文件数",
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
        dry_run = arguments.get("dry_run", True)
        force = arguments.get("force", False)
        media_file_ids: List[int] = arguments.get("media_file_ids") or []
        limit = min(arguments.get("limit", 20), 100)

        # 未指定 ID 时，自动收集已识别但未整理的文件
        if not media_file_ids:
            query = (
                select(MediaFile.id)
                .where(
                    MediaFile.organized == False,  # noqa: E712
                    MediaFile.media_type.isnot(None),
                )
                .order_by(MediaFile.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(query)
            media_file_ids = [row[0] for row in result.all()]

        if not media_file_ids:
            return {
                "success": True,
                "message": "没有待整理的媒体文件",
                "result": {"success_count": 0, "failed_count": 0, "skipped_count": 0},
            }

        result = await MediaOrganizerService.batch_organize(
            db,
            media_file_ids=media_file_ids,
            dry_run=dry_run,
            force=force,
        )

        # batch_organize 在配置错误时返回 {"status": "error", ...}
        if result.get("status") == "error":
            return {"success": False, "error": result.get("message", "整理失败")}

        mode = "预览" if dry_run else "整理"
        return {
            "success": True,
            "message": (
                f"{mode}完成：成功 {result.get('success_count', 0)}，"
                f"失败 {result.get('failed_count', 0)}，"
                f"跳过 {result.get('skipped_count', 0)}"
                + ("（dry_run 预览，未实际移动文件）" if dry_run else "")
            ),
            "dry_run": dry_run,
            "result": result,
        }
