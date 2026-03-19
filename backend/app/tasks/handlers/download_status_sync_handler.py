# -*- coding: utf-8 -*-
"""
下载状态同步任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.models.download_task import DownloadTask
from app.services.download.download_task_service import DownloadTaskService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.event import EVENT_DOWNLOAD_COMPLETED, EVENT_DOWNLOAD_FAILED
from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class DownloadStatusSyncHandler(BaseTaskHandler):
    """同步下载状态任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行同步下载状态

        Args:
            db: 数据库会话
            params: 处理器参数 (当前无参数)
            execution_id: 任务执行ID

        Returns:
            同步结果
        """
        await TaskExecutionService.append_log(db, execution_id, "开始同步下载任务状态")

        # 查询所有活跃任务（pending、downloading、seeding）
        result = await db.execute(
            select(DownloadTask).where(
                DownloadTask.status.in_(["pending", "downloading", "seeding"])
            )
        )
        tasks = result.scalars().all()

        await TaskExecutionService.append_log(db, execution_id, f"找到 {len(tasks)} 个活跃任务")

        completed_count = 0
        error_count = 0
        failed_count = 0

        for idx, download_task in enumerate(tasks):
            try:
                # 记录同步前的状态
                old_status = download_task.status
                old_progress = download_task.progress

                # 更新进度
                progress = int((idx + 1) / len(tasks) * 100) if len(tasks) > 0 else 100
                await TaskExecutionService.update_progress(db, execution_id, progress)

                # 同步任务状态
                updated_task = await DownloadTaskService.sync_task_status(db, download_task.id)

                # 检查任务是否刚完成（状态从未完成变为完成）
                is_completed = (
                    updated_task
                    and updated_task.progress == 100
                    and updated_task.completed_at is not None
                    and old_progress < 100  # 刚刚完成
                )
                if is_completed:
                    completed_count += 1
                    await TaskExecutionService.append_log(
                        db, execution_id,
                        f"✓ 任务 {download_task.id} ({download_task.torrent_name}) 下载完成"
                    )

                    # 发布下载完成事件
                    await event_bus.publish(
                        EVENT_DOWNLOAD_COMPLETED,
                        {
                            "download_task_id": updated_task.id,
                            "task_hash": updated_task.task_hash,
                            "torrent_name": updated_task.torrent_name,
                            "media_type": updated_task.media_type,
                            "total_size": updated_task.total_size,
                            "size_gb": round(updated_task.total_size / (1024**3), 2) if updated_task.total_size else 0,
                            "save_path": updated_task.save_path or "./data/downloads",
                            "ratio": updated_task.ratio,
                            "related_type": "download_task",
                            "related_id": updated_task.id,
                        }
                    )
                    logger.info(f"已发布下载完成事件: {updated_task.torrent_name}")

                # 检查任务是否失败（状态变为 failed 或 error）
                is_failed = (
                    updated_task
                    and updated_task.status in ["failed", "error"]
                    and old_status not in ["failed", "error"]  # 刚刚失败
                )
                if is_failed:
                    failed_count += 1
                    # 发布下载失败事件
                    await event_bus.publish(
                        EVENT_DOWNLOAD_FAILED,
                        {
                            "download_task_id": updated_task.id,
                            "task_hash": updated_task.task_hash,
                            "torrent_name": updated_task.torrent_name,
                            "media_type": updated_task.media_type,
                            "error_message": updated_task.error_message or "未知错误",
                            "related_type": "download_task",
                            "related_id": updated_task.id,
                        }
                    )
                    logger.warning(f"已发布下载失败事件: {updated_task.torrent_name}")

            except Exception as e:
                error_count += 1
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"✗ 同步任务 {download_task.id} 失败: {str(e)}"
                )

        await TaskExecutionService.update_progress(db, execution_id, 100)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"同步完成: 检查 {len(tasks)} 个任务, 完成 {completed_count} 个, 失败 {failed_count} 个, 错误 {error_count} 个"
        )

        return {
            "total_tasks": len(tasks),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "error_count": error_count
        }
