# -*- coding: utf-8 -*-
"""
统一资源刷新任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.models.resource_mapping import ResourceMapping
from app.models.pt_resource import PTResource
from app.services.pt.pt_resource_service import PTResourceService
from app.services.identification.unified_tv_series_service import UnifiedTVSeriesService
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class UnifiedResourceRefreshHandler(BaseTaskHandler):
    """刷新统一资源关联的PT资源任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行统一资源刷新

        Args:
            db: 数据库会话
            params: 处理器参数
                - unified_table_name: 统一资源表名 (必需，如 "unified_tv_series")
                - unified_resource_id: 统一资源ID (必需)
                - resource_ids: 指定要刷新的资源ID列表 (可选，为空则刷新全部)
            execution_id: 任务执行ID

        Returns:
            刷新结果
        """
        unified_table_name = params.get("unified_table_name")
        unified_resource_id = params.get("unified_resource_id")
        specified_resource_ids = params.get("resource_ids")

        if not unified_table_name or not unified_resource_id:
            raise ValueError("统一资源刷新任务缺少unified_table_name或unified_resource_id参数")

        # 初始化进度
        await TaskExecutionService.update_progress(db, execution_id, 0)

        # 确定刷新范围
        if specified_resource_ids:
            await TaskExecutionService.append_log(
                db, execution_id,
                f"开始刷新 {unified_table_name} ID={unified_resource_id} 的 {len(specified_resource_ids)} 个指定PT资源"
            )
            pt_resource_ids = specified_resource_ids
        else:
            await TaskExecutionService.append_log(
                db, execution_id,
                f"开始刷新 {unified_table_name} ID={unified_resource_id} 的所有关联PT资源"
            )
            # 获取关联的PT资源ID列表
            mappings_query = (
                select(PTResource.id)
                .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
                .where(
                    ResourceMapping.unified_table_name == unified_table_name,
                    ResourceMapping.unified_resource_id == unified_resource_id
                )
            )
            mappings_result = await db.execute(mappings_query)
            pt_resource_ids = [row[0] for row in mappings_result.all()]

        if not pt_resource_ids:
            await TaskExecutionService.update_progress(db, execution_id, 100)
            await TaskExecutionService.append_log(
                db, execution_id, "该资源没有关联的PT资源"
            )
            return {
                "unified_table_name": unified_table_name,
                "unified_resource_id": unified_resource_id,
                "total": 0,
                "success": 0,
                "failed": 0
            }

        total = len(pt_resource_ids)
        await TaskExecutionService.append_log(
            db, execution_id, f"找到 {total} 个关联的PT资源，开始批量刷新"
        )

        # 批量刷新资源（添加请求限速，避免频率过高）
        import asyncio
        success_count = 0
        failed_count = 0
        errors = []

        for index, resource_id in enumerate(pt_resource_ids):
            try:
                await PTResourceService.refresh_resource(db, resource_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({
                    "resource_id": resource_id,
                    "error": str(e)
                })
                logger.warning(f"Failed to refresh resource {resource_id}: {str(e)}")

            # 更新进度
            progress = int((index + 1) / total * 90)  # 0-90%
            await TaskExecutionService.update_progress(db, execution_id, progress)

            # 请求限速：每个请求后等待2秒，避免触发API频率限制
            # ⚠️ 重要：MTeam 对频率限制很严格，建议至少等待2秒
            if index < total - 1:  # 最后一个请求不需要等待
                await asyncio.sleep(2.0)

        await TaskExecutionService.append_log(
            db, execution_id,
            f"刷新完成: 成功 {success_count}/{total}, 失败 {failed_count}"
        )

        # 更新统一资源的统计信息
        if unified_table_name == "unified_tv_series":
            tv = await UnifiedTVSeriesService.get_by_id(db, unified_resource_id)
            if tv:
                await tv.update_statistics(db)
                await TaskExecutionService.append_log(
                    db, execution_id, "已更新电视剧统计信息"
                )
        # TODO: 支持其他资源类型（电影、音乐等）

        # 完成进度
        await TaskExecutionService.update_progress(db, execution_id, 100)

        result = {
            "unified_table_name": unified_table_name,
            "unified_resource_id": unified_resource_id,
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "errors": errors
        }

        logger.info(
            f"Unified resource refresh completed: {unified_table_name} ID={unified_resource_id}, "
            f"{success_count}/{total} succeeded, {failed_count} failed"
        )

        return result
