# -*- coding: utf-8 -*-
"""
PT资源识别任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.identification.resource_identify_service import ResourceIdentificationService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.event import EVENT_RESOURCE_IDENTIFIED
from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class PTResourceIdentifyHandler(BaseTaskHandler):
    """PT资源识别任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行批量识别

        Args:
            db: 数据库会话
            params: 处理器参数
                模式1（工作流自动触发）:
                - pt_resource_ids: PT资源ID列表 (必需)
                - media_type: 媒体类型 (默认 'auto')
                - skip_errors: 是否跳过错误 (默认 True)

                模式2（手动触发）:
                - limit: 识别数量 (必需)
                - category: 资源分类 (可选，如 movie, tv, music 等)
                - site_id: 站点ID (可选)
                - media_type: 媒体类型 (默认 'auto')
                - skip_errors: 是否跳过错误 (默认 True)
            execution_id: 任务执行ID

        Returns:
            识别结果
        """
        # 判断使用哪种模式
        pt_resource_ids = params.get("pt_resource_ids", [])

        if not pt_resource_ids:
            # 模式2：根据 limit 和 category 查询未识别资源
            from app.services.pt.pt_resource_service import PTResourceService

            limit = params.get("limit", 100)
            category = params.get("category")
            site_id = params.get("site_id")

            await TaskExecutionService.append_log(
                db, execution_id,
                f"查询未识别资源 (数量: {limit}, 分类: {category or '全部'}, 站点: {site_id or '全部'})"
            )

            # 查询未识别资源
            unidentified_resources = await PTResourceService.get_unidentified_resources(
                db, site_id=site_id, category=category, limit=limit
            )

            if not unidentified_resources:
                await TaskExecutionService.append_log(
                    db, execution_id, "没有找到未识别的资源"
                )
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "error_count": 0
                }

            pt_resource_ids = [r.id for r in unidentified_resources]
            await TaskExecutionService.append_log(
                db, execution_id,
                f"找到 {len(pt_resource_ids)} 个未识别资源"
            )

        media_type = params.get("media_type", "auto")
        skip_errors = params.get("skip_errors", True)

        # 初始化进度
        await TaskExecutionService.update_progress(
            db, execution_id, 0,
            progress_detail={
                "total": len(pt_resource_ids),
                "processed": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
            }
        )
        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始识别 {len(pt_resource_ids)} 个PT资源, 媒体类型: {media_type}"
        )

        # 执行批量识别（传入execution_id用于进度更新）
        result = await ResourceIdentificationService.batch_identify_resources(
            db=db,
            pt_resource_ids=pt_resource_ids,
            media_type=media_type,
            skip_errors=skip_errors,
            task_execution_id=execution_id
        )

        # 最终进度设为100
        await TaskExecutionService.update_progress(db, execution_id, 100)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"PT资源识别完成: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}"
        )

        # 发布资源识别完成事件
        # 尝试从 handler_params 中获取 user_id（手动触发的任务）
        user_id = params.get("user_id")

        # 如果没有 user_id，则作为广播消息（系统任务）
        event_data = {
            "total": result["total"],
            "success": result["success"],
            "failed": result["failed"],
            "skipped": result["skipped"],
            "media_type": media_type,
            "related_type": "task_execution",
            "related_id": execution_id,
        }

        # 如果有 user_id，则添加到事件数据中
        if user_id:
            event_data["user_id"] = user_id
        else:
            # 系统任务，作为广播消息
            event_data["broadcast"] = True

        await event_bus.publish(EVENT_RESOURCE_IDENTIFIED, event_data)

        logger.info(
            f"已发布资源识别完成事件: 成功 {result['success']} 个, "
            f"通知类型: {'用户通知' if user_id else '系统广播'}"
        )

        return {
            "total": result["total"],
            "success": result["success"],
            "failed": result["failed"],
            "skipped": result["skipped"],
            "error_count": len(result.get("errors", []))
        }
