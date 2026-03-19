# -*- coding: utf-8 -*-
"""
榜单同步任务处理器（阶段一：快速落表）

注意：此处理器仅执行阶段一（快速落表），不处理详情同步。
详情同步由 TrendingDetailSyncHandler 处理。
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.trending.trending_sync_service import TrendingSyncService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.trending import (
    COLLECTION_TYPES,
    DEFAULT_TRENDING_SYNC_COUNT,
)

logger = logging.getLogger(__name__)


class TrendingSyncHandler(BaseTaskHandler):
    """榜单同步任务处理器（阶段一：快速落表）"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行榜单同步（阶段一）

        工作流程：
        1. 调用适配器获取榜单基础信息
        2. 快速写入 trending_collections 表
        3. 不处理详情同步（由 TrendingDetailSyncHandler 异步处理）

        Args:
            db: 数据库会话
            params: 处理器参数
                - collection_types: 榜单类型列表（可选，默认全部）
                - count: 每个榜单同步数量（可选，默认100）
                - trigger_detail_sync: 是否触发详情同步任务（可选，默认True）
            execution_id: 任务执行ID

        Returns:
            执行结果统计
        """
        # 解析参数
        collection_types = params.get("collection_types") or COLLECTION_TYPES
        count = params.get("count", DEFAULT_TRENDING_SYNC_COUNT)
        trigger_detail_sync = params.get("trigger_detail_sync", True)

        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"开始同步榜单（阶段一：快速落表），共 {len(collection_types)} 个榜单，每榜 {count} 条",
        )

        # 初始化进度
        await TaskExecutionService.update_progress(db, execution_id, 0)

        # 同步所有榜单
        results = []
        for i, collection_type in enumerate(collection_types):
            try:
                await TaskExecutionService.append_log(
                    db,
                    execution_id,
                    f"正在同步榜单 ({i+1}/{len(collection_types)}): {collection_type}",
                )

                result = await TrendingSyncService.sync_collection(
                    db, collection_type, count
                )
                results.append(result)

                # 更新进度
                progress = int(((i + 1) / len(collection_types)) * 100)
                await TaskExecutionService.update_progress(
                    db,
                    execution_id,
                    progress,
                    progress_detail={
                        "current_collection": collection_type,
                        "completed": i + 1,
                        "total": len(collection_types),
                    },
                )

            except Exception as e:
                logger.error(f"同步榜单 {collection_type} 失败: {str(e)}")
                results.append({
                    "collection_type": collection_type,
                    "error": str(e),
                })

        # 统计结果
        total_fetched = sum(r.get("fetched_count", 0) for r in results if "error" not in r)
        total_inserted = sum(r.get("inserted_count", 0) for r in results if "error" not in r)
        total_pending = sum(r.get("pending_detail_sync", 0) for r in results if "error" not in r)
        error_count = sum(1 for r in results if "error" in r)

        # 最终进度
        await TaskExecutionService.update_progress(
            db,
            execution_id,
            100,
            progress_detail={
                "total_collections": len(collection_types),
                "success_collections": len(results) - error_count,
                "error_collections": error_count,
                "total_fetched": total_fetched,
                "total_inserted": total_inserted,
                "pending_detail_sync": total_pending,
            },
        )

        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"榜单同步（阶段一）完成：获取 {total_fetched} 条，插入 {total_inserted} 条，"
            f"待详情同步 {total_pending} 条",
        )

        # 触发详情同步任务（可选）
        if trigger_detail_sync and total_pending > 0:
            await TaskExecutionService.append_log(
                db,
                execution_id,
                f"提示：有 {total_pending} 条记录待详情同步，请手动执行\"榜单详情同步\"任务",
            )

        return {
            "results": results,
            "total_collections": len(collection_types),
            "success_collections": len(results) - error_count,
            "error_collections": error_count,
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "pending_detail_sync": total_pending,
        }
