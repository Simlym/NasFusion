"""
数据模型
"""
from app.models.base import Base, BaseModel, IDMixin, TimestampMixin
from app.models.notification import (
    NotificationChannel,
    NotificationInternal,
    NotificationRule,
    NotificationTemplate,
    NotificationExternal,
)
from app.models.pt_site import PTSite
from app.models.pt_metadata import (
    PTCategory,
    PTVideoCodec,
    PTAudioCodec,
    PTStandard,
    PTSource,
    PTLanguage,
    PTCountry,
)
from app.models.pt_resource import PTResource
from app.models.pt_resource_detail import PTResourceDetail
from app.models.user import User, UserProfile
from app.models.login_history import LoginHistory
from app.models.sync_log import SyncLog
from app.models.unified_movie import UnifiedMovie
from app.models.resource_mapping import ResourceMapping
from app.models.downloader_config import DownloaderConfig
from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.media_directory import MediaDirectory
from app.models.organize_config import OrganizeConfig
from app.models.scheduled_task import ScheduledTask
from app.models.task_execution import TaskExecution
from app.models.image_cache import ImageCache
from app.models.subscription import Subscription
from app.models.subscription_check_log import SubscriptionCheckLog
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_adult import UnifiedAdult
from app.models.media_server_config import MediaServerConfig
from app.models.media_server_watch_history import MediaServerWatchHistory
from app.models.media_server_library_stats import MediaServerLibraryStats
from app.models.media_server_item import MediaServerItem
from app.models.storage_mount import StorageMount
from app.models.ai_agent import (
    AIAgentConfig,
    AIConversation,
    AIMessage,
    AIToolExecution,
)

__all__ = [
    "Base",
    "BaseModel",
    "IDMixin",
    "TimestampMixin",
    "User",
    "UserProfile",
    "LoginHistory",
    "NotificationChannel",
    "NotificationInternal",
    "NotificationRule",
    "NotificationTemplate",
    "NotificationExternal",
    "PTSite",
    "PTCategory",
    "PTVideoCodec",
    "PTAudioCodec",
    "PTStandard",
    "PTSource",
    "PTLanguage",
    "PTCountry",
    "PTResource",
    "PTResourceDetail",
    "SyncLog",
    "UnifiedMovie",
    "ResourceMapping",
    "DownloaderConfig",
    "DownloadTask",
    "MediaFile",
    "MediaDirectory",
    "OrganizeConfig",
    "ScheduledTask",
    "TaskExecution",
    "ImageCache",
    "Subscription",
    "SubscriptionCheckLog",
    "UnifiedTVSeries",
    "UnifiedAdult",
    "MediaServerConfig",
    "MediaServerWatchHistory",
    "MediaServerLibraryStats",
    "MediaServerItem",
    "StorageMount",
    "AIAgentConfig",
    "AIConversation",
    "AIMessage",
    "AIToolExecution",
]
