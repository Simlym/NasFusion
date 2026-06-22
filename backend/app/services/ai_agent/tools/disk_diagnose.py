# -*- coding: utf-8 -*-
"""
磁盘诊断工具（只读）

以数据库中已登记的 storage_mounts / media_files / download_tasks 作为索引，
对记录到的路径做 stat 检查，快速给出存储健康诊断。

设计要点：
- **只读**：不删除/不移动任何文件，清理动作交由专门的（危险）工具，
  并经二次确认协议执行
- **有界**：不全盘遍历，只 stat 数据库已登记的路径，并受 limit 限制
- 阻塞 IO 统一走 asyncio.to_thread，避免卡住事件循环
"""
import asyncio
import logging
import os
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ORGANIZE_MODE_HARDLINK,
    ORGANIZE_MODE_REFLINK,
    ORGANIZE_MODE_SYMLINK,
    TASK_STATUS_COMPLETED,
)
from app.constants.ai_agent import AGENT_TOOL_DISK_DIAGNOSE
from app.models import DownloadTask, MediaFile
from app.services.ai_agent.tool_registry import BaseTool, register_tool
from app.services.storage.storage_mount_service import StorageMountService

logger = logging.getLogger(__name__)

# 告警阈值
_USAGE_WARN_PERCENT = 90.0
_FREE_WARN_BYTES = 20 * 1024 ** 3  # 剩余空间低于 20GB 告警
_DEFAULT_LIMIT = 500
_MAX_LIMIT = 2000
# 明细返回上限，避免单次结果过大撑爆上下文
_DETAIL_CAP = 50
# 这些模式下源文件应当持续存在（move/copy 模式源消失属正常）
_LINK_MODES = (ORGANIZE_MODE_HARDLINK, ORGANIZE_MODE_REFLINK, ORGANIZE_MODE_SYMLINK)


def _gb(num_bytes: Any) -> float:
    """字节转 GB（保留两位），None/0 返回 0.0。"""
    if not num_bytes:
        return 0.0
    return round(num_bytes / (1024 ** 3), 2)


@register_tool
class DiskDiagnoseTool(BaseTool):
    """磁盘与存储健康诊断（只读）"""

    name = AGENT_TOOL_DISK_DIAGNOSE
    description = (
        "磁盘与存储健康诊断（只读，不删除任何文件）。"
        "check=storage 报告各挂载点空间使用与告警（剩余不足/使用率过高/不可访问）；"
        "check=broken_links 扫描媒体库失效链接与链接源文件丢失；"
        "check=orphan_torrents 扫描下载任务的种子文件丢失 / 完成数据目录丢失；"
        "check=all 全部执行。适合回答「磁盘是否快满了」「媒体库有没有断链」。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "check": {
                "type": "string",
                "description": "诊断项，默认 all",
                "enum": ["all", "storage", "broken_links", "orphan_torrents"],
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "路径扫描上限（broken_links/orphan_torrents 生效），默认 500，最大 2000",
                "default": _DEFAULT_LIMIT,
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
        check = arguments.get("check", "all")
        try:
            limit = min(max(int(arguments.get("limit", _DEFAULT_LIMIT)), 1), _MAX_LIMIT)
        except (TypeError, ValueError):
            limit = _DEFAULT_LIMIT

        checks: Dict[str, Any] = {}
        warnings: List[str] = []

        if check in ("all", "storage"):
            checks["storage"] = await cls._check_storage(db, warnings)
        if check in ("all", "broken_links"):
            checks["broken_links"] = await cls._check_broken_links(db, limit, warnings)
        if check in ("all", "orphan_torrents"):
            checks["orphan_torrents"] = await cls._check_orphan_torrents(db, limit, warnings)

        return {
            "success": True,
            "checks": checks,
            "has_warnings": bool(warnings),
            "warnings": warnings,
            "message": (
                f"诊断完成，发现 {len(warnings)} 项需关注：{'；'.join(warnings)}"
                if warnings
                else "诊断完成，存储状态良好，未发现明显问题"
            ),
            "note": "本工具只读；如需清理请使用对应的删除工具（删除前会再次向你确认）。",
        }

    # ==================== 各诊断项 ====================

    @classmethod
    async def _check_storage(cls, db: AsyncSession, warnings: List[str]) -> Dict[str, Any]:
        """挂载点空间使用诊断。"""
        try:
            await StorageMountService.refresh_disk_info(db)
        except Exception as e:  # 刷新失败不致命，沿用上次缓存值
            logger.warning(f"刷新磁盘信息失败: {e}")

        mounts = await StorageMountService.get_all_mounts(db, is_enabled=True)
        items: List[Dict[str, Any]] = []
        for m in mounts:
            percent = m.usage_percent
            level = "ok"
            if not m.is_accessible:
                level = "critical"
                warnings.append(f"挂载点[{m.name}]不可访问（{m.container_path}）")
            elif percent is not None and percent >= _USAGE_WARN_PERCENT:
                level = "warning"
                warnings.append(f"挂载点[{m.name}]使用率 {percent}%")
            elif m.free_space is not None and m.free_space < _FREE_WARN_BYTES:
                level = "warning"
                warnings.append(f"挂载点[{m.name}]剩余仅 {_gb(m.free_space)}GB")

            items.append({
                "name": m.name,
                "type": m.mount_type,
                "path": m.container_path,
                "category": m.media_category,
                "accessible": m.is_accessible,
                "total_gb": _gb(m.total_space),
                "used_gb": _gb(m.used_space),
                "free_gb": _gb(m.free_space),
                "usage_percent": percent,
                "level": level,
            })
        return {"mount_count": len(items), "mounts": items}

    @classmethod
    async def _check_broken_links(
        cls, db: AsyncSession, limit: int, warnings: List[str]
    ) -> Dict[str, Any]:
        """媒体库失效链接 / 链接源文件丢失诊断。"""
        result = await db.execute(
            select(MediaFile)
            .where(MediaFile.organized == True)  # noqa: E712
            .order_by(MediaFile.id.desc())
            .limit(limit)
        )
        files = list(result.scalars().all())

        def _scan() -> tuple[list, list]:
            broken_targets: List[Dict[str, Any]] = []
            missing_sources: List[Dict[str, Any]] = []
            for f in files:
                # 整理后的媒体库路径丢失 → 媒体库出现断链
                if f.organized_path and not os.path.exists(f.organized_path):
                    broken_targets.append({
                        "id": f.id,
                        "name": f.file_name,
                        "path": f.organized_path,
                        "mode": f.organize_mode,
                    })
                # 链接模式下源文件丢失 → 链接已悬空（move/copy 源消失属正常，跳过）
                if (
                    f.file_path
                    and f.organize_mode in _LINK_MODES
                    and not os.path.exists(f.file_path)
                ):
                    missing_sources.append({
                        "id": f.id,
                        "name": f.file_name,
                        "path": f.file_path,
                        "mode": f.organize_mode,
                    })
            return broken_targets, missing_sources

        broken_targets, missing_sources = await asyncio.to_thread(_scan)
        if broken_targets:
            warnings.append(f"媒体库失效链接 {len(broken_targets)} 个")
        if missing_sources:
            warnings.append(f"链接源文件丢失 {len(missing_sources)} 个")

        return {
            "scanned": len(files),
            "scan_limited": len(files) >= limit,
            "broken_link_count": len(broken_targets),
            "broken_links": broken_targets[:_DETAIL_CAP],
            "missing_source_count": len(missing_sources),
            "missing_sources": missing_sources[:_DETAIL_CAP],
        }

    @classmethod
    async def _check_orphan_torrents(
        cls, db: AsyncSession, limit: int, warnings: List[str]
    ) -> Dict[str, Any]:
        """下载任务种子文件丢失 / 完成数据目录丢失诊断。"""
        result = await db.execute(
            select(DownloadTask).order_by(DownloadTask.id.desc()).limit(limit)
        )
        tasks = list(result.scalars().all())

        def _scan() -> tuple[list, list]:
            missing_torrent_files: List[Dict[str, Any]] = []
            missing_data: List[Dict[str, Any]] = []
            for t in tasks:
                # DB 记录了 .torrent 路径但文件已不在
                if t.torrent_file_path and not os.path.exists(t.torrent_file_path):
                    missing_torrent_files.append({
                        "id": t.id,
                        "name": t.torrent_name,
                        "torrent_file": t.torrent_file_path,
                    })
                # 已完成任务的数据目录已不存在（被外部删除）
                if (
                    t.status == TASK_STATUS_COMPLETED
                    and t.save_path
                    and not os.path.exists(t.save_path)
                ):
                    missing_data.append({
                        "id": t.id,
                        "name": t.torrent_name,
                        "save_path": t.save_path,
                    })
            return missing_torrent_files, missing_data

        missing_torrent_files, missing_data = await asyncio.to_thread(_scan)
        if missing_torrent_files:
            warnings.append(f"种子文件丢失 {len(missing_torrent_files)} 个")
        if missing_data:
            warnings.append(f"完成任务数据目录丢失 {len(missing_data)} 个")

        return {
            "scanned": len(tasks),
            "scan_limited": len(tasks) >= limit,
            "missing_torrent_file_count": len(missing_torrent_files),
            "missing_torrent_files": missing_torrent_files[:_DETAIL_CAP],
            "missing_data_count": len(missing_data),
            "missing_data": missing_data[:_DETAIL_CAP],
        }
