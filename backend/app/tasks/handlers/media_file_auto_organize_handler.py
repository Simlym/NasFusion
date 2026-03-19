# -*- coding: utf-8 -*-
"""
媒体文件自动整理任务处理器
下载完成后自动整理文件到媒体库
"""
import logging
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.mediafile.media_file_service import MediaFileService
from app.services.mediafile.media_organizer_service import MediaOrganizerService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.event import EVENT_MEDIA_ORGANIZED
from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class MediaFileAutoOrganizeHandler(BaseTaskHandler):
    """下载完成后自动整理媒体文件"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行自动整理

        Args:
            db: 数据库会话
            params: 处理器参数
                - download_task_id: 下载任务ID (必需)
                - save_path: 下载保存路径 (必需)
                - organize_config_id: 整理配置ID (可选，从下载任务读取)
                - storage_mount_id: 存储挂载点ID (可选，从下载任务读取)
            execution_id: 任务执行ID

        Returns:
            整理结果
        """
        from app.models.download_task import DownloadTask
        from app.models.organize_config import OrganizeConfig
        from app.models.storage_mount import StorageMount

        download_task_id = params.get("download_task_id")
        save_path = params.get("save_path")

        if not download_task_id:
            error_msg = "缺少必需参数: download_task_id"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "error", "message": error_msg}

        # 获取下载任务
        download_task = await db.get(DownloadTask, download_task_id)
        if not download_task:
            error_msg = f"下载任务不存在: {download_task_id}"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "error", "message": error_msg}

        # 检查是否启用自动整理
        if not download_task.auto_organize:
            msg = f"下载任务 {download_task_id} 未启用自动整理，跳过"
            await TaskExecutionService.append_log(db, execution_id, msg)
            return {"status": "skipped", "message": msg}

        # 检查整理配置
        if not download_task.organize_config_id:
            error_msg = f"下载任务 {download_task_id} 未指定整理配置"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "error", "message": error_msg}

        organize_config = await db.get(OrganizeConfig, download_task.organize_config_id)
        if not organize_config:
            error_msg = f"整理配置不存在: {download_task.organize_config_id}"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "error", "message": error_msg}

        # 检查存储挂载点
        if not download_task.storage_mount_id:
            error_msg = f"下载任务 {download_task_id} 未指定存储挂载点"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "error", "message": error_msg}

        storage_mount = await db.get(StorageMount, download_task.storage_mount_id)
        if not storage_mount:
            error_msg = f"存储挂载点不存在: {download_task.storage_mount_id}"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            return {"status": "error", "message": error_msg}

        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始自动整理: {download_task.torrent_name}\n"
            f"  整理配置: {organize_config.name}\n"
            f"  存储挂载点: {storage_mount.name} ({storage_mount.container_path})"
        )

        # 初始化进度
        await TaskExecutionService.update_progress(db, execution_id, 0)

        # 第一步: 扫描下载目录
        await TaskExecutionService.append_log(db, execution_id, "→ 扫描下载目录...")
        await TaskExecutionService.update_progress(db, execution_id, 10)

        scan_result = await MediaFileService.scan_directory(
            db=db,
            directory=save_path,
            recursive=True,
        )

        files_found = scan_result.get("files", 0)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"✓ 扫描完成，发现 {files_found} 个媒体文件"
        )
        await TaskExecutionService.update_progress(db, execution_id, 20)

        if files_found == 0:
            msg = "下载目录中未发现媒体文件"
            await TaskExecutionService.append_log(db, execution_id, msg)
            return {"status": "success", "message": msg, "organized_count": 0}

        # 第二步: 查询下载路径下的媒体文件并关联到下载任务
        from sqlalchemy import select, update
        from app.models.media_file import MediaFile
        from pathlib import Path

        # 规范化路径用于比较
        # 统一使用正斜杠，并确保以 / 结尾，防止 /Down 匹配到 /Downloads
        save_path_normalized = str(Path(save_path).resolve()).replace('\\', '/')
        if not save_path_normalized.endswith('/'):
            save_path_normalized += '/'

        # 查询该路径下的所有媒体文件（精确匹配目录前缀）
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.file_path.like(f"{save_path_normalized}%")
            )
        )
        media_files = result.scalars().all()

        # 批量更新 download_task_id（仅更新尚未关联的文件，避免覆盖已有关联）
        if media_files:
            unlinked_file_ids = [f.id for f in media_files if f.download_task_id is None]
            if unlinked_file_ids:
                await db.execute(
                    update(MediaFile)
                    .where(MediaFile.id.in_(unlinked_file_ids))
                    .values(download_task_id=download_task_id)
                )
            await db.commit()

            await TaskExecutionService.append_log(
                db, execution_id,
                f"✓ 已关联 {len(unlinked_file_ids)}/{len(media_files)} 个文件到下载任务"
            )
        await TaskExecutionService.update_progress(db, execution_id, 30)

        # 第三步: 整理文件
        await TaskExecutionService.append_log(
            db, execution_id,
            f"→ 开始整理 {len(media_files)} 个文件..."
        )

        success_count = 0
        failed_count = 0
        skipped_count = 0
        organize_results = []

        for idx, media_file in enumerate(media_files):
            # 更新进度 (30-90%)
            progress = 30 + int((idx / len(media_files)) * 60)
            await TaskExecutionService.update_progress(db, execution_id, progress)

            # 检查文件是否已识别
            if not media_file.unified_resource_id:
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"⚠ 跳过未识别文件: {media_file.file_name}"
                )
                skipped_count += 1
                continue

            # 执行整理
            result = await MediaOrganizerService.organize_media_file(
                db=db,
                media_file=media_file,
                config=organize_config,
                dry_run=False,
            )

            organize_results.append({
                "file_id": media_file.id,
                "file_name": media_file.file_name,
                **result
            })

            if result["status"] == "success":
                success_count += 1
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"✓ 整理成功: {media_file.file_name} → {result.get('organized_path')}"
                )
            elif result["status"] == "skipped":
                skipped_count += 1
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"⊘ 跳过: {media_file.file_name} - {result.get('message')}"
                )
            else:
                failed_count += 1
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"✗ 失败: {media_file.file_name} - {result.get('message')}"
                )

        # 完成
        await TaskExecutionService.update_progress(db, execution_id, 100)

        summary = (
            f"自动整理完成:\n"
            f"  成功: {success_count}\n"
            f"  失败: {failed_count}\n"
            f"  跳过: {skipped_count}"
        )
        await TaskExecutionService.append_log(db, execution_id, summary)

        # 发布事件
        if success_count > 0:
            await event_bus.publish(EVENT_MEDIA_ORGANIZED, {
                "user_id": download_task.user_id,  # 下载任务的创建者
                "download_task_id": download_task_id,
                "torrent_name": download_task.torrent_name,
                "organized_count": success_count,
                "storage_mount": storage_mount.name,
                "related_type": "download_task",
                "related_id": download_task_id,
            })

        return {
            "status": "success",
            "message": summary,
            "organized_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "details": organize_results,
        }
