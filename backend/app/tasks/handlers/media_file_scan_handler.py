# -*- coding: utf-8 -*-
"""
媒体文件扫描任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.mediafile.media_file_service import MediaFileService
from app.services.mediafile.media_directory_service import MediaDirectoryService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.event import EVENT_MEDIA_SCAN_COMPLETED
from app.constants import SCAN_MODE_FULL, SCAN_MODE_INCREMENTAL
from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class MediaFileScanHandler(BaseTaskHandler):
    """扫描媒体文件目录任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行媒体扫描

        Args:
            db: 数据库会话
            params: 处理器参数
                - directory: 要扫描的目录路径 (可选)
                - mount_type: 按挂载点类型扫描 (可选)
                - recursive: 是否递归扫描 (默认 True)
                - media_type: 媒体类型过滤 (可选)
                - scan_mode: 扫描模式 (full/incremental, 默认 full)
            execution_id: 任务执行ID

        Returns:
            扫描结果
        """
        from sqlalchemy import select
        from app.models.storage_mount import StorageMount

        directory = params.get("directory")
        mount_type = params.get("mount_type")
        recursive = params.get("recursive", True)
        media_type = params.get("media_type")
        scan_mode = params.get("scan_mode", SCAN_MODE_FULL)

        # 确定要扫描的目录列表
        directories_to_scan = []
        if directory:
            directories_to_scan.append(directory)
        elif mount_type:
            # 修改逻辑：如果是扫描媒体库，且指定了媒体类型，则只扫描对应分类的挂载点
            stmt = select(StorageMount.container_path).where(StorageMount.mount_type == mount_type, StorageMount.is_enabled == True)
            if mount_type == 'library' and media_type:
                stmt = stmt.where(StorageMount.media_category == media_type)
            result = await db.execute(stmt)
            directories_to_scan = [r for r in result.scalars().all()]
        
        if not directories_to_scan:
            error_msg = f"没有可扫描的目录 (directory={directory}, mount_type={mount_type})"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "skipped", "message": error_msg}

        # 初始化进度
        await TaskExecutionService.update_progress(db, execution_id, 0)
        
        total_stats = {
            "files_created": 0,
            "directories_created": 0,
            "directories_updated": 0,
            "deleted_files": 0,
            "deleted_directories": 0,
            "total_issues": 0
        }

        for i, current_dir in enumerate(directories_to_scan):
            dir_progress_start = int((i / len(directories_to_scan)) * 100)
            dir_progress_end = int(((i + 1) / len(directories_to_scan)) * 100)
            
            await TaskExecutionService.append_log(
                db, execution_id, f"开始扫描第 {i+1}/{len(directories_to_scan)} 个目录: {current_dir} (模式: {scan_mode})"
            )

            # 步骤1: 扫描文件和目录
            # 增量模式下 force=False，允许基于 mtime 跳过未变更目录
            force_scan = scan_mode != SCAN_MODE_INCREMENTAL
            scan_result = await MediaFileService.scan_directory(
                db,
                directory=current_dir,
                recursive=recursive,
                media_type=media_type,
                force=force_scan,
            )
            
            # 统计扫描结果
            total_stats["directories_created"] += scan_result.get("directories_created", 0)
            total_stats["directories_updated"] += scan_result.get("directories_updated", 0)
            total_stats["files_created"] += scan_result.get("files", 0)
            
            # 步骤2: 清理不存在的文件
            deleted = await MediaFileService.delete_orphaned_records(db, current_dir)
            total_stats["deleted_files"] += deleted

            # 步骤3: 清理孤立目录
            deleted_dirs = await MediaDirectoryService.delete_orphaned_directories(db, current_dir)
            total_stats["deleted_directories"] += deleted_dirs
            
            await TaskExecutionService.update_progress(db, execution_id, dir_progress_end)

        # 步骤4: 统一检测问题 (全局检测，不分目录)
        await TaskExecutionService.append_log(db, execution_id, "检测全局目录问题...")
        issues = await MediaDirectoryService.detect_issues(db)
        total_stats["total_issues"] = sum(issues.values())

        # 完成进度
        await TaskExecutionService.update_progress(db, execution_id, 100)
        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"所有扫描任务完成: 目录 {len(directories_to_scan)} 个, 新增目录 {total_stats['directories_created']}, 更新目录 {total_stats['directories_updated']}, 清理文件 {total_stats['deleted_files']}, 清理目录 {total_stats['deleted_directories']}, 发现问题 {total_stats['total_issues']}",
        )

        # 发布媒体扫描完成事件
        # 尝试从 handler_params 中获取 user_id（手动触发的任务）
        user_id = params.get("user_id")

        event_data = {
            "mount_type": mount_type,
            "scan_mode": scan_mode,
            "total_directories_scanned": len(directories_to_scan),
            "related_type": "task_execution",
            "related_id": execution_id,
            **total_stats
        }

        # 如果有 user_id，则添加到事件数据中
        if user_id:
            event_data["user_id"] = user_id
        else:
            # 系统任务，作为广播消息
            event_data["broadcast"] = True

        await event_bus.publish(EVENT_MEDIA_SCAN_COMPLETED, event_data)
        
        return {
            "status": "success",
            "directories_scanned": len(directories_to_scan),
            **total_stats
        }
