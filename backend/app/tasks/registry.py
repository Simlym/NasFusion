# -*- coding: utf-8 -*-
"""
任务处理器注册表
"""
import logging
from typing import Dict, Type, Optional

from app.tasks.base import BaseTaskHandler

logger = logging.getLogger(__name__)


class TaskHandlerRegistry:
    """任务处理器注册表"""

    _handlers: Dict[str, Type[BaseTaskHandler]] = {}

    @classmethod
    def register(cls, task_type: str, handler_class: Type[BaseTaskHandler]):
        """注册处理器"""
        cls._handlers[task_type] = handler_class
        logger.debug(f"已注册任务处理器: {task_type} -> {handler_class.__name__}")

    @classmethod
    def get_handler(cls, task_type: str) -> Optional[Type[BaseTaskHandler]]:
        """获取处理器"""
        return cls._handlers.get(task_type)

    @classmethod
    def get_all_handlers(cls) -> Dict[str, Type[BaseTaskHandler]]:
        """获取所有已注册的处理器"""
        return cls._handlers.copy()


def register_all_handlers():
    """注册所有任务处理器"""
    from app.constants import (
        TASK_TYPE_PT_RESOURCE_SYNC,
        TASK_TYPE_PT_RESOURCE_IDENTIFY,
        TASK_TYPE_SUBSCRIPTION_CHECK,
        TASK_TYPE_MEDIA_FILE_SCAN,
        TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
        TASK_TYPE_DOWNLOAD_CREATE,
        TASK_TYPE_DOWNLOAD_STATUS_SYNC,
        TASK_TYPE_TASK_EXECUTION_CLEANUP,
        TASK_TYPE_UNIFIED_RESOURCE_REFRESH,
        TASK_TYPE_MEDIA_SERVER_WATCH_HISTORY_SYNC,
        TASK_TYPE_MEDIA_SERVER_LIBRARY_STATS_UPDATE,
        TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
        TASK_TYPE_TRENDING_SYNC,
        TASK_TYPE_TRENDING_DETAIL_SYNC,
        TASK_TYPE_PERSON_DETAIL_SYNC,
        TASK_TYPE_CREDITS_BACKFILL,
        TASK_TYPE_PERSON_MERGE,
        TASK_TYPE_DUPLICATE_MEDIA_MERGE,
    )
    from app.tasks.handlers import (
        PTResourceSyncHandler,
        PTResourceIdentifyHandler,
        SubscriptionCheckHandler,
        MediaFileScanHandler,
        MediaFileAutoOrganizeHandler,
        DownloadCreateHandler,
        DownloadStatusSyncHandler,
        TaskExecutionCleanupHandler,
        UnifiedResourceRefreshHandler,
        MediaServerWatchHistorySyncHandler,
        MediaServerLibraryStatsHandler,
        MediaServerLibrarySyncHandler,
        TrendingSyncHandler,
        TrendingDetailSyncHandler,
        PersonDetailSyncHandler,
        CreditsBackfillHandler,
        PersonMergeHandler,
        DuplicateMediaMergeHandler,
    )

    TaskHandlerRegistry.register(TASK_TYPE_PT_RESOURCE_SYNC, PTResourceSyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_PT_RESOURCE_IDENTIFY, PTResourceIdentifyHandler)
    TaskHandlerRegistry.register(TASK_TYPE_SUBSCRIPTION_CHECK, SubscriptionCheckHandler)
    TaskHandlerRegistry.register(TASK_TYPE_MEDIA_FILE_SCAN, MediaFileScanHandler)
    TaskHandlerRegistry.register(TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE, MediaFileAutoOrganizeHandler)
    TaskHandlerRegistry.register(TASK_TYPE_DOWNLOAD_CREATE, DownloadCreateHandler)
    TaskHandlerRegistry.register(TASK_TYPE_DOWNLOAD_STATUS_SYNC, DownloadStatusSyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_TASK_EXECUTION_CLEANUP, TaskExecutionCleanupHandler)
    TaskHandlerRegistry.register(TASK_TYPE_UNIFIED_RESOURCE_REFRESH, UnifiedResourceRefreshHandler)
    TaskHandlerRegistry.register(TASK_TYPE_MEDIA_SERVER_WATCH_HISTORY_SYNC, MediaServerWatchHistorySyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_MEDIA_SERVER_LIBRARY_STATS_UPDATE, MediaServerLibraryStatsHandler)
    TaskHandlerRegistry.register(TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC, MediaServerLibrarySyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_TRENDING_SYNC, TrendingSyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_TRENDING_DETAIL_SYNC, TrendingDetailSyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_PERSON_DETAIL_SYNC, PersonDetailSyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_CREDITS_BACKFILL, CreditsBackfillHandler)
    TaskHandlerRegistry.register(TASK_TYPE_PERSON_MERGE, PersonMergeHandler)
    TaskHandlerRegistry.register(TASK_TYPE_DUPLICATE_MEDIA_MERGE, DuplicateMediaMergeHandler)

    logger.debug(f"已注册 {len(TaskHandlerRegistry.get_all_handlers())} 个任务处理器")

