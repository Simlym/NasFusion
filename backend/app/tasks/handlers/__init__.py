# -*- coding: utf-8 -*-
"""任务处理器实现"""
from app.tasks.handlers.pt_resource_sync_handler import PTResourceSyncHandler
from app.tasks.handlers.pt_resource_identify_handler import PTResourceIdentifyHandler
from app.tasks.handlers.subscription_check_handler import SubscriptionCheckHandler
from app.tasks.handlers.media_file_scan_handler import MediaFileScanHandler
from app.tasks.handlers.media_file_auto_organize_handler import MediaFileAutoOrganizeHandler
from app.tasks.handlers.download_create_handler import DownloadCreateHandler
from app.tasks.handlers.download_status_sync_handler import DownloadStatusSyncHandler
from app.tasks.handlers.task_execution_cleanup_handler import TaskExecutionCleanupHandler
from app.tasks.handlers.unified_resource_refresh_handler import UnifiedResourceRefreshHandler
from app.tasks.handlers.media_server_watch_history_sync_handler import MediaServerWatchHistorySyncHandler
from app.tasks.handlers.media_server_library_stats_handler import MediaServerLibraryStatsHandler
from app.tasks.handlers.media_server_library_sync_handler import MediaServerLibrarySyncHandler
from app.tasks.handlers.media_server_batch_rematch_handler import MediaServerBatchRematchHandler
from app.tasks.handlers.trending_sync_handler import TrendingSyncHandler
from app.tasks.handlers.trending_detail_sync_handler import TrendingDetailSyncHandler
from app.tasks.handlers.person_detail_sync_handler import PersonDetailSyncHandler
from app.tasks.handlers.credits_backfill_handler import CreditsBackfillHandler
from app.tasks.handlers.person_merge_handler import PersonMergeHandler

__all__ = [
    "PTResourceSyncHandler",
    "PTResourceIdentifyHandler",
    "SubscriptionCheckHandler",
    "MediaFileScanHandler",
    "MediaFileAutoOrganizeHandler",
    "DownloadCreateHandler",
    "DownloadStatusSyncHandler",
    "TaskExecutionCleanupHandler",
    "UnifiedResourceRefreshHandler",
    "MediaServerWatchHistorySyncHandler",
    "MediaServerLibraryStatsHandler",
    "MediaServerLibrarySyncHandler",
    "MediaServerBatchRematchHandler",
    "TrendingSyncHandler",
    "TrendingDetailSyncHandler",
    "PersonDetailSyncHandler",
    "CreditsBackfillHandler",
    "PersonMergeHandler",
]

