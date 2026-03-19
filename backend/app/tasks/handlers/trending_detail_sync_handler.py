# -*- coding: utf-8 -*-
"""
榜单详情同步任务处理器

用于异步处理 trending_collections 的详情同步（阶段二）
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.trending.trending_sync_service import TrendingSyncService
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class TrendingDetailSyncHandler(BaseTaskHandler):
    """榜单详情同步任务处理器"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行榜单详情同步

        Args:
            db: 数据库会话
            params: 处理器参数
                - collection_type: 榜单类型（可选，不指定则处理所有）
                - batch_size: 每批处理数量（可选，默认20）
                - max_batches: 最大批次数（可选，默认50）
            execution_id: 任务执行ID

        Returns:
            执行结果统计
        """
        # 解析参数
        collection_type = params.get("collection_type")
        batch_size = params.get("batch_size", 20)
        max_batches = params.get("max_batches", 50)

        # 获取待同步数量
        pending_count = await TrendingSyncService.get_pending_detail_count(
            db, collection_type
        )

        if pending_count == 0:
            await TaskExecutionService.append_log(
                db, execution_id, "没有待同步的榜单详情"
            )
            return {
                "pending_count": 0,
                "processed_count": 0,
                "success_count": 0,
                "error_count": 0,
            }

        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"开始同步榜单详情，待处理: {pending_count} 条，"
            f"批大小: {batch_size}，最大批次: {max_batches}",
        )

        await TaskExecutionService.update_progress(db, execution_id, 0)

        # 分批处理
        total_processed = 0
        total_success = 0
        total_error = 0
        batch_count = 0

        while batch_count < max_batches:
            # 执行一批
            result = await TrendingSyncService.sync_collection_details(
                db,
                collection_type=collection_type,
                batch_size=batch_size,
            )

            processed = result.get("processed_count", 0)
            if processed == 0:
                break  # 没有更多待处理记录

            total_processed += processed
            total_success += result.get("success_count", 0)
            total_error += result.get("error_count", 0)
            batch_count += 1

            # 更新进度
            progress = min(int((total_processed / pending_count) * 100), 100)
            await TaskExecutionService.update_progress(
                db,
                execution_id,
                progress,
                progress_detail={
                    "batch": batch_count,
                    "processed": total_processed,
                    "pending": pending_count,
                    "success": total_success,
                    "error": total_error,
                },
            )

            await TaskExecutionService.append_log(
                db,
                execution_id,
                f"批次 {batch_count}: 处理 {processed} 条，"
                f"成功 {result.get('success_count', 0)} 条",
            )

        # 最终进度
        await TaskExecutionService.update_progress(
            db,
            execution_id,
            100,
            progress_detail={
                "total_batches": batch_count,
                "total_processed": total_processed,
                "total_success": total_success,
                "total_error": total_error,
            },
        )

        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"榜单详情同步完成：处理 {total_processed} 条，"
            f"成功 {total_success} 条，失败 {total_error} 条",
        )

        return {
            "pending_count": pending_count,
            "processed_count": total_processed,
            "success_count": total_success,
            "error_count": total_error,
            "batch_count": batch_count,
        }
