# -*- coding: utf-8 -*-
"""
业务事件类型定义

这些常量定义系统中的业务事件（而非处理方式）。
事件是业务领域的客观事实，可被多个事件处理器监听。

事件总线架构：
    业务系统 → 发布事件 → 事件总线 → 多个处理器
                                    ├── notification_handler (发送通知)
                                    ├── audit_handler (记录审计)
                                    ├── statistics_handler (更新统计)
                                    └── workflow_handler (触发后续任务)
"""

# ============================================================================
# 下载相关事件 (Download Events)
# ============================================================================

EVENT_DOWNLOAD_STARTED = "download_started"
"""下载已开始"""

EVENT_DOWNLOAD_COMPLETED = "download_completed"
"""下载已完成"""

EVENT_DOWNLOAD_FAILED = "download_failed"
"""下载已失败"""

EVENT_DOWNLOAD_PAUSED = "download_paused"
"""下载已暂停"""


# ============================================================================
# 订阅相关事件 (Subscription Events)
# ============================================================================

EVENT_SUBSCRIPTION_MATCHED = "subscription_matched"
"""订阅匹配到资源"""

EVENT_SUBSCRIPTION_DOWNLOADED = "subscription_downloaded"
"""订阅资源已下载"""

EVENT_SUBSCRIPTION_COMPLETED = "subscription_completed"
"""订阅已完成（所有集数下载完毕）"""

EVENT_SUBSCRIPTION_NO_RESOURCE = "subscription_no_resource"
"""订阅检查但无新资源"""


# ============================================================================
# 资源相关事件 (Resource Events)
# ============================================================================

EVENT_RESOURCE_FREE_PROMOTION = "resource_free_promotion"
"""发现免费促销资源"""

EVENT_RESOURCE_2X_PROMOTION = "resource_2x_promotion"
"""发现 2x 促销资源"""

EVENT_RESOURCE_HIGH_QUALITY = "resource_high_quality"
"""发现高质量资源"""

EVENT_RESOURCE_IDENTIFIED = "resource_identified"
"""资源识别完成"""


# ============================================================================
# PT 站点相关事件 (PT Site Events)
# ============================================================================

EVENT_SITE_CONNECTION_FAILED = "site_connection_failed"
"""站点连接失败"""

EVENT_SITE_AUTH_EXPIRED = "site_auth_expired"
"""站点认证过期"""

EVENT_SITE_SYNC_COMPLETED = "site_sync_completed"
"""站点同步完成"""


# ============================================================================
# 媒体文件相关事件 (Media File Events)
# ============================================================================

EVENT_MEDIA_SCAN_COMPLETED = "media_scan_completed"
"""媒体扫描完成"""

EVENT_MEDIA_ORGANIZED = "media_organized"
"""媒体文件已整理"""

EVENT_MEDIA_METADATA_SCRAPED = "media_metadata_scraped"
"""媒体元数据已刮削"""


# ============================================================================
# 媒体服务器相关事件 (Media Server Events)
# ============================================================================

EVENT_MEDIA_SERVER_LIBRARY_REFRESHED = "media_server_library_refreshed"
"""媒体服务器媒体库已刷新"""

EVENT_MEDIA_SERVER_WATCH_HISTORY_SYNCED = "media_server_watch_history_synced"
"""媒体服务器观看历史已同步"""

EVENT_MEDIA_SERVER_CONNECTION_FAILED = "media_server_connection_failed"
"""媒体服务器连接失败"""


# ============================================================================
# 任务相关事件 (Task Events)
# ============================================================================

EVENT_TASK_FAILED = "task_failed"
"""任务执行失败"""

EVENT_TASK_COMPLETED = "task_completed"
"""任务执行完成"""


# ============================================================================
# 系统相关事件 (System Events)
# ============================================================================

EVENT_SYSTEM_ERROR = "system_error"
"""系统错误"""

EVENT_DISK_SPACE_LOW = "disk_space_low"
"""磁盘空间不足"""

EVENT_USER_LOGIN_ANOMALY = "user_login_anomaly"
"""用户登录异常"""

EVENT_SYSTEM_UPDATE_AVAILABLE = "system_update_available"
"""系统更新可用"""


# ============================================================================
# 所有事件类型列表
# ============================================================================

ALL_EVENTS = [
    # 下载相关
    EVENT_DOWNLOAD_STARTED,
    EVENT_DOWNLOAD_COMPLETED,
    EVENT_DOWNLOAD_FAILED,
    EVENT_DOWNLOAD_PAUSED,
    # 订阅相关
    EVENT_SUBSCRIPTION_MATCHED,
    EVENT_SUBSCRIPTION_DOWNLOADED,
    EVENT_SUBSCRIPTION_COMPLETED,
    EVENT_SUBSCRIPTION_NO_RESOURCE,
    # 资源相关
    EVENT_RESOURCE_FREE_PROMOTION,
    EVENT_RESOURCE_2X_PROMOTION,
    EVENT_RESOURCE_HIGH_QUALITY,
    EVENT_RESOURCE_IDENTIFIED,
    # PT站点相关
    EVENT_SITE_CONNECTION_FAILED,
    EVENT_SITE_AUTH_EXPIRED,
    EVENT_SITE_SYNC_COMPLETED,
    # 媒体文件相关
    EVENT_MEDIA_SCAN_COMPLETED,
    EVENT_MEDIA_ORGANIZED,
    EVENT_MEDIA_METADATA_SCRAPED,
    # 媒体服务器相关
    EVENT_MEDIA_SERVER_LIBRARY_REFRESHED,
    EVENT_MEDIA_SERVER_WATCH_HISTORY_SYNCED,
    EVENT_MEDIA_SERVER_CONNECTION_FAILED,
    # 任务相关
    EVENT_TASK_FAILED,
    EVENT_TASK_COMPLETED,
    # 系统相关
    EVENT_SYSTEM_ERROR,
    EVENT_DISK_SPACE_LOW,
    EVENT_USER_LOGIN_ANOMALY,
    EVENT_SYSTEM_UPDATE_AVAILABLE,
]
