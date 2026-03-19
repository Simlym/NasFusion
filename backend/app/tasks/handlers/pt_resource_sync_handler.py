# -*- coding: utf-8 -*-
"""
PT资源同步任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.pt.pt_resource_service import PTResourceService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.event import EVENT_SITE_SYNC_COMPLETED
from app.events.bus import event_bus
from app.models.pt_site import PTSite

logger = logging.getLogger(__name__)


class PTResourceSyncHandler(BaseTaskHandler):
    """PT资源同步任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行PT站点同步

        Args:
            db: 数据库会话
            params: 处理器参数
                - site_id: 站点ID (必需)
                - sync_type: 同步类型 (默认 'incremental')
                - max_pages: 最大页数 (可选)
                - start_page: 起始页 (默认 1)
                - mode: 资源模式 (可选)
                - categories: 分类列表 (可选)
                - upload_date_start: 上传开始时间 (可选)
                - upload_date_end: 上传结束时间 (可选)
                - keyword: 关键字搜索 (可选)
                - sortField: 排序字段 (可选)
                - sortDirection: 排序方向 (可选)
                - request_interval: 请求间隔秒数 (可选，默认使用站点配置)
            execution_id: 任务执行ID

        Returns:
            同步结果
        """
        site_id = params.get("site_id")
        if not site_id:
            raise ValueError("PT同步任务缺少site_id参数")

        sync_type = params.get("sync_type", "incremental")
        max_pages = params.get("max_pages")
        start_page = params.get("start_page", 1)
        request_interval = params.get("request_interval")  # 任务级请求间隔

        # 提取过滤参数
        filters = {}
        if params.get("mode"):
            filters["mode"] = params["mode"]
        if params.get("categories"):
            filters["categories"] = params["categories"]
        if params.get("upload_date_start"):
            filters["upload_date_start"] = params["upload_date_start"]
        if params.get("upload_date_end"):
            filters["upload_date_end"] = params["upload_date_end"]
        if params.get("keyword"):
            filters["keyword"] = params["keyword"]
        if params.get("sortField"):
            filters["sortField"] = params["sortField"]
        if params.get("sortDirection"):
            filters["sortDirection"] = params["sortDirection"]

        # 更新进度
        filter_desc = ""
        if filters:
            filter_parts = []
            if filters.get("mode"):
                filter_parts.append(f"模式:{filters['mode']}")
            if filters.get("categories"):
                filter_parts.append(f"分类:{','.join(filters['categories'])}")
            if filters.get("keyword"):
                filter_parts.append(f"关键字:{filters['keyword']}")
            filter_desc = f" (过滤: {', '.join(filter_parts)})"

        await TaskExecutionService.append_log(
            db, execution_id, f"开始同步站点 {site_id}, 类型: {sync_type}{filter_desc}"
        )

        # 执行同步（传入 execution_id 用于实时进度更新）
        sync_log = await PTResourceService.sync_site_resources(
            db, site_id, sync_type, max_pages, start_page,
            task_execution_id=execution_id,
            filters=filters if filters else None,
            request_interval=request_interval
        )

        # 最终进度设为100
        await TaskExecutionService.update_progress(
            db, execution_id, 100,
            progress_detail={
                "pages_processed": sync_log.pages_processed,
                "resources_found": sync_log.resources_found,
                "resources_new": sync_log.resources_new,
                "resources_updated": sync_log.resources_updated,
                "errors": sync_log.resources_error,
                "filters": filters,
            }
        )
        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"同步完成: 新增 {sync_log.resources_new}, 更新 {sync_log.resources_updated}",
        )

        # 查询站点信息（用于事件发布）
        site = await db.get(PTSite, site_id)

        # 发布同步完成事件
        if site:
            # 尝试从 handler_params 中获取 user_id（手动触发的任务）
            user_id = params.get("user_id")

            event_data = {
                "site_id": site_id,
                "site_name": site.name,
                "sync_log_id": sync_log.id,
                "sync_type": sync_type,
                "resources_found": sync_log.resources_found,
                "resources_new": sync_log.resources_new,
                "resources_updated": sync_log.resources_updated,
                "pages_processed": sync_log.pages_processed,
                "duration": sync_log.duration,
                "filters": filters,
                "related_type": "sync_log",
                "related_id": sync_log.id,
            }

            # 如果有 user_id，则添加到事件数据中
            if user_id:
                event_data["user_id"] = user_id
            else:
                # 系统任务，作为广播消息
                event_data["broadcast"] = True

            await event_bus.publish(EVENT_SITE_SYNC_COMPLETED, event_data)
            logger.info(
                f"已发布同步完成事件: 站点 {site.name}, 新增 {sync_log.resources_new} 个资源, "
                f"通知类型: {'用户通知' if user_id else '系统广播'}"
            )

        return {
            "sync_log_id": sync_log.id,
            "resources_found": sync_log.resources_found,
            "resources_new": sync_log.resources_new,
            "resources_updated": sync_log.resources_updated,
            "pages_processed": sync_log.pages_processed,
            "filters": filters,
        }
