# -*- coding: utf-8 -*-
"""
MCP Resources 提供者

暴露 NasFusion 的关键数据给外部 MCP Client（如 Claude Desktop）。

Resource URI 设计：
- nasfusion://downloads/{status} - 下载任务（pending/active/completed/failed）
- nasfusion://media/{type} - 媒体库（recent/stats/movies/tv）
- nasfusion://subscriptions/{filter} - 订阅（active/all）
- nasfusion://system/status - 系统状态
- nasfusion://tasks/{filter} - 任务（recent/pending/failed）
- nasfusion://pt/sites - PT 站点状态
- nasfusion://storage/usage - 存储使用情况
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.timezone import now as tz_now

from app.constants.download_task import (
    DOWNLOAD_STATUS_COMPLETED,
    DOWNLOAD_STATUS_DOWNLOADING,
    DOWNLOAD_STATUS_ERROR,
    DOWNLOAD_STATUS_PENDING,
)
from app.models import (
    DownloadTask,
    MediaServerItem,
    StorageMount,
    Subscription,
    TaskExecution,
    PTSite,
)

logger = logging.getLogger(__name__)


class MCPResourceProvider:
    """MCP 资源提供者"""

    # 资源 URI 前缀
    URI_PREFIX = "nasfusion://"

    @classmethod
    def list_resources(cls) -> List[Dict[str, str]]:
        """
        列出所有可用资源
        
        Returns:
            资源列表，每个资源包含 uri, name, description, mimeType
        """
        return [
            {
                "uri": f"{cls.URI_PREFIX}downloads/pending",
                "name": "待处理下载",
                "description": "等待下载的任务列表",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}downloads/active",
                "name": "活跃下载",
                "description": "正在下载的任务列表",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}downloads/recent",
                "name": "最近下载",
                "description": "最近完成的下载任务",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}media/recent",
                "name": "最近添加媒体",
                "description": "媒体库中最近添加的影视",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}media/stats",
                "name": "媒体库统计",
                "description": "媒体库整体统计信息",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}subscriptions/active",
                "name": "活跃订阅",
                "description": "正在追踪的订阅列表",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}system/status",
                "name": "系统状态",
                "description": "NasFusion 系统整体状态",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}tasks/recent",
                "name": "最近任务",
                "description": "最近执行的任务记录",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}pt/sites",
                "name": "PT站点状态",
                "description": "已配置PT站点的状态",
                "mimeType": "application/json",
            },
            {
                "uri": f"{cls.URI_PREFIX}storage/usage",
                "name": "存储使用",
                "description": "存储空间使用情况",
                "mimeType": "application/json",
            },
        ]

    @classmethod
    async def read_resource(cls, db: AsyncSession, user_id: int, uri: str) -> Optional[str]:
        """
        读取资源内容
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            uri: 资源 URI
            
        Returns:
            资源内容（JSON 字符串）或 None
        """
        if not uri.startswith(cls.URI_PREFIX):
            return None

        path = uri[len(cls.URI_PREFIX):]
        parts = path.split("/")

        if len(parts) < 2:
            return None

        category = parts[0]
        identifier = parts[1]

        try:
            if category == "downloads":
                return await cls._get_downloads(db, identifier, user_id)
            elif category == "media":
                return await cls._get_media(db, identifier, user_id)
            elif category == "subscriptions":
                return await cls._get_subscriptions(db, identifier, user_id)
            elif category == "system":
                return await cls._get_system_status(db, user_id)
            elif category == "tasks":
                return await cls._get_tasks(db, identifier, user_id)
            elif category == "pt":
                return await cls._get_pt_sites(db, user_id)
            elif category == "storage":
                return await cls._get_storage(db, user_id)
            else:
                return None
        except Exception as e:
            logger.exception(f"读取资源失败: {uri}")
            return json.dumps({
                "error": f"读取资源失败: {str(e)}",
                "uri": uri,
            }, ensure_ascii=False)

    @classmethod
    async def _get_downloads(cls, db: AsyncSession, status: str, user_id: int) -> str:
        """获取下载任务"""
        limit = 20

        if status == "pending":
            query = select(DownloadTask).where(
                DownloadTask.user_id == user_id,
                DownloadTask.status.in_([DOWNLOAD_STATUS_PENDING, "queued"]),
            ).order_by(desc(DownloadTask.created_at)).limit(limit)
        elif status == "active":
            query = select(DownloadTask).where(
                DownloadTask.user_id == user_id,
                DownloadTask.status == DOWNLOAD_STATUS_DOWNLOADING,
            ).order_by(desc(DownloadTask.updated_at)).limit(limit)
        elif status == "recent":
            query = select(DownloadTask).where(
                DownloadTask.user_id == user_id,
                DownloadTask.status.in_([DOWNLOAD_STATUS_COMPLETED, DOWNLOAD_STATUS_ERROR]),
            ).order_by(desc(DownloadTask.updated_at)).limit(limit)
        else:
            return json.dumps({"error": "无效的状态"}, ensure_ascii=False)

        result = await db.execute(query)
        tasks = result.scalars().all()

        return json.dumps({
            "status": status,
            "count": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title or "未知标题",
                    "status": t.status,
                    "progress": getattr(t, 'progress', None),
                    "size": getattr(t, 'total_size', None),
                    "downloaded": getattr(t, 'downloaded_size', None),
                    "speed": getattr(t, 'download_speed', None),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in tasks
            ],
        }, ensure_ascii=False, indent=2)

    @classmethod
    async def _get_media(cls, db: AsyncSession, type_: str, user_id: int) -> str:
        """获取媒体库信息"""
        if type_ == "recent":
            # 最近添加的媒体
            query = select(MediaServerItem).where(
                MediaServerItem.user_id == user_id,
            ).order_by(desc(MediaServerItem.created_at)).limit(20)
            result = await db.execute(query)
            items = result.scalars().all()

            return json.dumps({
                "type": "recent",
                "count": len(items),
                "items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "type": item.media_type,
                        "year": item.year,
                        "library": item.library_name,
                        "added_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in items
                ],
            }, ensure_ascii=False, indent=2)

        elif type_ == "stats":
            # 统计信息
            movie_count = await db.scalar(
                select(func.count(MediaServerItem.id)).where(
                    MediaServerItem.user_id == user_id,
                    MediaServerItem.media_type == "movie",
                )
            )
            tv_count = await db.scalar(
                select(func.count(MediaServerItem.id)).where(
                    MediaServerItem.user_id == user_id,
                    MediaServerItem.media_type == "tv",
                )
            )

            return json.dumps({
                "type": "stats",
                "movies": movie_count or 0,
                "tv_series": tv_count or 0,
                "total": (movie_count or 0) + (tv_count or 0),
            }, ensure_ascii=False, indent=2)

        return json.dumps({"error": "无效的类型"}, ensure_ascii=False)

    @classmethod
    async def _get_subscriptions(cls, db: AsyncSession, filter_: str, user_id: int) -> str:
        """获取订阅信息"""
        query = select(Subscription).where(
            Subscription.user_id == user_id,
        )

        if filter_ == "active":
            query = query.where(Subscription.is_active.is_(True))

        query = query.order_by(desc(Subscription.updated_at)).limit(50)
        result = await db.execute(query)
        subs = result.scalars().all()

        return json.dumps({
            "filter": filter_,
            "count": len(subs),
            "subscriptions": [
                {
                    "id": s.id,
                    "title": s.title,
                    "type": s.media_type,
                    "is_active": s.is_active,
                    "quality_preference": s.quality_preference,
                    "last_check_at": s.last_check_at.isoformat() if s.last_check_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in subs
            ],
        }, ensure_ascii=False, indent=2)

    @classmethod
    async def _get_system_status(cls, db: AsyncSession, user_id: int) -> str:
        """获取系统状态"""
        # 统计各类数据
        download_count = await db.scalar(
            select(func.count(DownloadTask.id)).where(DownloadTask.user_id == user_id)
        )
        media_count = await db.scalar(
            select(func.count(MediaServerItem.id)).where(MediaServerItem.user_id == user_id)
        )
        sub_count = await db.scalar(
            select(func.count(Subscription.id)).where(Subscription.user_id == user_id)
        )
        site_count = await db.scalar(
            select(func.count(PTSite.id)).where(PTSite.user_id == user_id)
        )

        # 活跃下载
        active_downloads = await db.scalar(
            select(func.count(DownloadTask.id)).where(
                DownloadTask.user_id == user_id,
                DownloadTask.status == DOWNLOAD_STATUS_DOWNLOADING,
            )
        )

        # 失败任务
        failed_tasks = await db.scalar(
            select(func.count(TaskExecution.id)).where(
                TaskExecution.user_id == user_id,
                TaskExecution.status == "failed",
            )
        )

        return json.dumps({
            "status": "running",
            "stats": {
                "downloads": {
                    "total": download_count or 0,
                    "active": active_downloads or 0,
                },
                "media_items": media_count or 0,
                "subscriptions": sub_count or 0,
                "pt_sites": site_count or 0,
                "failed_tasks": failed_tasks or 0,
            },
            "timestamp": tz_now().isoformat(),
        }, ensure_ascii=False, indent=2)

    @classmethod
    async def _get_tasks(cls, db: AsyncSession, filter_: str, user_id: int) -> str:
        """获取任务记录"""
        query = select(TaskExecution).where(
            TaskExecution.user_id == user_id,
        )

        if filter_ == "recent":
            query = query.order_by(desc(TaskExecution.created_at)).limit(20)
        elif filter_ == "pending":
            query = query.where(TaskExecution.status == "pending").limit(20)
        elif filter_ == "failed":
            query = query.where(TaskExecution.status == "failed").order_by(
                desc(TaskExecution.created_at)
            ).limit(20)
        else:
            query = query.order_by(desc(TaskExecution.created_at)).limit(20)

        result = await db.execute(query)
        tasks = result.scalars().all()

        return json.dumps({
            "filter": filter_,
            "count": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "result": t.result,
                    "error_message": t.error_message,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in tasks
            ],
        }, ensure_ascii=False, indent=2)

    @classmethod
    async def _get_pt_sites(cls, db: AsyncSession, user_id: int) -> str:
        """获取 PT 站点状态"""
        query = select(PTSite).where(PTSite.user_id == user_id)
        result = await db.execute(query)
        sites = result.scalars().all()

        return json.dumps({
            "count": len(sites),
            "sites": [
                {
                    "id": s.id,
                    "name": s.name,
                    "is_enabled": s.is_enabled,
                    "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
                    "cookie_valid": getattr(s, 'cookie_valid', None),
                }
                for s in sites
            ],
        }, ensure_ascii=False, indent=2)

    @classmethod
    async def _get_storage(cls, db: AsyncSession, user_id: int) -> str:
        """获取存储使用情况"""
        query = select(StorageMount).where(StorageMount.user_id == user_id)
        result = await db.execute(query)
        mounts = result.scalars().all()

        return json.dumps({
            "count": len(mounts),
            "mounts": [
                {
                    "id": m.id,
                    "name": m.name,
                    "path": m.mount_path,
                    "type": getattr(m, 'storage_type', "local"),
                    "is_active": getattr(m, 'is_active', True),
                }
                for m in mounts
            ],
        }, ensure_ascii=False, indent=2)
