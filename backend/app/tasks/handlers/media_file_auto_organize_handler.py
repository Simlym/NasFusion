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
            raise ValueError(error_msg)

        # 获取下载任务
        download_task = await db.get(DownloadTask, download_task_id)
        if not download_task:
            error_msg = f"下载任务不存在: {download_task_id}"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            raise ValueError(error_msg)

        if params.get("workflow_token") and params["workflow_token"] != download_task.workflow_token:
            raise ValueError("原下载任务已删除，此执行记录不能操作后来添加的下载")
        execution = await TaskExecutionService.get_by_id(db, execution_id)
        if execution and execution.created_at < download_task.created_at:
            raise ValueError("此整理记录早于当前下载，原下载任务可能已删除")

        # 检查是否启用自动整理
        if not download_task.auto_organize:
            msg = f"下载任务 {download_task_id} 未启用自动整理，跳过"
            await TaskExecutionService.append_log(db, execution_id, msg)
            return {"status": "skipped", "message": msg}

        # 检查整理配置
        if not download_task.organize_config_id:
            error_msg = f"下载任务 {download_task_id} 未指定整理配置"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            raise ValueError(error_msg)

        organize_config = await db.get(OrganizeConfig, download_task.organize_config_id)
        if not organize_config:
            error_msg = f"整理配置不存在: {download_task.organize_config_id}"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            raise ValueError(error_msg)

        # 检查存储挂载点
        if not download_task.storage_mount_id:
            error_msg = f"下载任务 {download_task_id} 未指定存储挂载点"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            raise ValueError(error_msg)

        storage_mount = await db.get(StorageMount, download_task.storage_mount_id)
        if not storage_mount:
            error_msg = f"存储挂载点不存在: {download_task.storage_mount_id}"
            await TaskExecutionService.append_log(db, execution_id, error_msg)
            raise ValueError(error_msg)

        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始自动整理: {download_task.torrent_name}\n"
            f"  整理配置: {organize_config.name}\n"
            f"  存储挂载点: {storage_mount.name} ({storage_mount.container_path})"
        )

        # 初始化进度
        await TaskExecutionService.update_progress(db, execution_id, 0)

        # 只发现本次种子对应的文件，不能扫描共享下载目录并认领其他种子。
        # 重启后源文件可能已移动，必须同时读取之前落库的文件检查点。
        from sqlalchemy import select
        from app.models.media_file import MediaFile

        save_path = download_task.save_path or save_path
        media_files = (await db.execute(
            select(MediaFile).where(MediaFile.download_task_id == download_task_id)
        )).scalars().all()
        source_available = bool(save_path and Path(save_path).exists())
        if not source_available and (not media_files or any(
            not f.organized and not (f.sub_status or {}).get("auto_organize_checkpoint")
            for f in media_files
        )):
            raise FileNotFoundError("下载路径不可用，等待存储就绪后重试")
        if not storage_mount.is_enabled:
            raise ValueError("目标存储挂载点已禁用")
        if not Path(storage_mount.container_path).is_dir():
            raise FileNotFoundError("目标存储路径不可用，等待挂载就绪后重试")

        if source_available:
            await MediaFileService.create_from_download_task(db, download_task)
        media_files = (await db.execute(
            select(MediaFile).where(MediaFile.download_task_id == download_task_id)
        )).scalars().all()
        if not media_files:
            raise RuntimeError("未发现本次下载的媒体文件，请检查挂载、路径映射或种子文件")
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

            # 文件级检查点：即使用户设置了覆盖，自动恢复也不重复整理已完成文件。
            if media_file.organized:
                if not media_file.organized_path or not Path(media_file.organized_path).exists():
                    failed_count += 1
                    await TaskExecutionService.append_log(
                        db, execution_id, f"已整理文件的目标不可用: {media_file.file_name}"
                    )
                else:
                    skipped_count += 1
                continue

            # 检查文件是否已识别
            if not media_file.unified_resource_id:
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"⚠ 跳过未识别文件: {media_file.file_name}"
                )
                failed_count += 1
                continue

            # 执行整理
            result = await MediaOrganizerService.organize_media_file(
                db=db,
                media_file=media_file,
                config=organize_config,
                dry_run=False,
                storage_mount_id=download_task.storage_mount_id,
                resume_safe=True,
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
                failed_count += 1
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

        summary = (
            f"本轮自动整理结果:\n"
            f"  成功: {success_count}\n"
            f"  失败: {failed_count}\n"
            f"  跳过: {skipped_count}"
        )
        await TaskExecutionService.append_log(db, execution_id, summary)

        if failed_count:
            raise RuntimeError(f"自动整理有 {failed_count} 个文件未完成，已完成文件将保留并在重试时跳过")

        await TaskExecutionService.update_progress(db, execution_id, 100)

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
