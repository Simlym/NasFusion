"""持久化工作流事件。"""

EVENT_PENDING = "pending"
EVENT_DELIVERED = "delivered"
DOWNLOAD_ORGANIZE_KEY_PREFIX = "download_completed:organize:"
SITE_SYNC_WORKFLOW_KEY_PREFIX = "site_sync:workflow:"
RESOURCE_IDENTIFY_WORKFLOW_KEY_PREFIX = "resource_identified:subscription:"
MEDIA_REFRESH_KEY_PREFIX = "media_organized:refresh:"
MEDIA_REFRESH_DEBOUNCE_SECONDS = 60
RECOVERY_POLL_SECONDS = 10
RECOVERY_CONCURRENCY = 2
