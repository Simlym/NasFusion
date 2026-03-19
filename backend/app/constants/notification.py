# -*- coding: utf-8 -*-
"""
通知系统常量定义

本文件包含通知系统的配置常量（优先级、渠道类型、状态等）。
业务事件常量已移至 app.constants.event 模块。

重构说明：
    - 事件定义: app.constants.event (业务事件，可被多个处理器监听)
    - 通知配置: app.constants.notification (通知系统专用配置)
"""

# 导入业务事件常量（用于事件优先级映射和默认启用配置）
from app.constants.event import (
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
    # PT站点相关
    EVENT_SITE_CONNECTION_FAILED,
    EVENT_SITE_AUTH_EXPIRED,
    EVENT_SITE_SYNC_COMPLETED,
    # 媒体文件相关
    EVENT_MEDIA_SCAN_COMPLETED,
    EVENT_MEDIA_ORGANIZED,
    EVENT_MEDIA_METADATA_SCRAPED,
    # 任务相关
    EVENT_TASK_FAILED,
    EVENT_TASK_COMPLETED,
    # 系统相关
    EVENT_SYSTEM_ERROR,
    EVENT_DISK_SPACE_LOW,
    EVENT_USER_LOGIN_ANOMALY,
    EVENT_SYSTEM_UPDATE_AVAILABLE,
)

# ============================================================================
# 通知优先级 (Notification Priority)
# ============================================================================

NOTIFICATION_PRIORITY_LOW = "low"
NOTIFICATION_PRIORITY_NORMAL = "normal"
NOTIFICATION_PRIORITY_HIGH = "high"
NOTIFICATION_PRIORITY_URGENT = "urgent"

NOTIFICATION_PRIORITIES = [
    NOTIFICATION_PRIORITY_LOW,
    NOTIFICATION_PRIORITY_NORMAL,
    NOTIFICATION_PRIORITY_HIGH,
    NOTIFICATION_PRIORITY_URGENT,
]

# ============================================================================
# 系统内消息状态 (System Notification Status)
# ============================================================================

NOTIFICATION_STATUS_UNREAD = "unread"
NOTIFICATION_STATUS_READ = "read"
NOTIFICATION_STATUS_ARCHIVED = "archived"

NOTIFICATION_STATUSES = [
    NOTIFICATION_STATUS_UNREAD,
    NOTIFICATION_STATUS_READ,
    NOTIFICATION_STATUS_ARCHIVED,
]

# ============================================================================
# 通知渠道类型 (Channel Types)
# ============================================================================

NOTIFICATION_CHANNEL_TELEGRAM = "telegram"
NOTIFICATION_CHANNEL_EMAIL = "email"
NOTIFICATION_CHANNEL_WEBHOOK = "webhook"
NOTIFICATION_CHANNEL_WECOM = "wecom"
NOTIFICATION_CHANNEL_DINGTALK = "dingtalk"
NOTIFICATION_CHANNEL_BARK = "bark"
NOTIFICATION_CHANNEL_DISCORD = "discord"
NOTIFICATION_CHANNEL_GOTIFY = "gotify"
NOTIFICATION_CHANNEL_PUSHPLUS = "pushplus"

NOTIFICATION_CHANNEL_TYPES = [
    NOTIFICATION_CHANNEL_TELEGRAM,
    NOTIFICATION_CHANNEL_EMAIL,
    NOTIFICATION_CHANNEL_WEBHOOK,
    NOTIFICATION_CHANNEL_WECOM,
    NOTIFICATION_CHANNEL_DINGTALK,
    NOTIFICATION_CHANNEL_BARK,
    NOTIFICATION_CHANNEL_DISCORD,
    NOTIFICATION_CHANNEL_GOTIFY,
    NOTIFICATION_CHANNEL_PUSHPLUS,
]

# ============================================================================
# 通知渠道状态 (Channel Status)
# ============================================================================

NOTIFICATION_CHANNEL_STATUS_HEALTHY = "healthy"
NOTIFICATION_CHANNEL_STATUS_ERROR = "error"
NOTIFICATION_CHANNEL_STATUS_TESTING = "testing"

NOTIFICATION_CHANNEL_STATUSES = [
    NOTIFICATION_CHANNEL_STATUS_HEALTHY,
    NOTIFICATION_CHANNEL_STATUS_ERROR,
    NOTIFICATION_CHANNEL_STATUS_TESTING,
]

# ============================================================================
# 通知发送状态 (Send Status)
# ============================================================================

NOTIFICATION_SEND_STATUS_PENDING = "pending"
NOTIFICATION_SEND_STATUS_SENT = "sent"
NOTIFICATION_SEND_STATUS_FAILED = "failed"

NOTIFICATION_SEND_STATUSES = [
    NOTIFICATION_SEND_STATUS_PENDING,
    NOTIFICATION_SEND_STATUS_SENT,
    NOTIFICATION_SEND_STATUS_FAILED,
]

# ============================================================================
# 通知模板格式 (Template Format)
# ============================================================================

NOTIFICATION_FORMAT_TEXT = "text"
NOTIFICATION_FORMAT_MARKDOWN = "markdown"
NOTIFICATION_FORMAT_HTML = "html"

NOTIFICATION_FORMATS = [
    NOTIFICATION_FORMAT_TEXT,
    NOTIFICATION_FORMAT_MARKDOWN,
    NOTIFICATION_FORMAT_HTML,
]

# ============================================================================
# 关联资源类型 (Related Resource Types)
# ============================================================================

NOTIFICATION_RELATED_PT_RESOURCE = "pt_resource"
NOTIFICATION_RELATED_SUBSCRIPTION = "subscription"
NOTIFICATION_RELATED_DOWNLOAD_TASK = "download_task"
NOTIFICATION_RELATED_MEDIA_FILE = "media_file"
NOTIFICATION_RELATED_PT_SITE = "pt_site"
NOTIFICATION_RELATED_TASK_EXECUTION = "task_execution"

NOTIFICATION_RELATED_TYPES = [
    NOTIFICATION_RELATED_PT_RESOURCE,
    NOTIFICATION_RELATED_SUBSCRIPTION,
    NOTIFICATION_RELATED_DOWNLOAD_TASK,
    NOTIFICATION_RELATED_MEDIA_FILE,
    NOTIFICATION_RELATED_PT_SITE,
    NOTIFICATION_RELATED_TASK_EXECUTION,
]

# ============================================================================
# 默认配置 (Default Settings)
# ============================================================================

# 默认消息过期时间（天）
DEFAULT_NOTIFICATION_EXPIRE_DAYS = 30

# 默认去重时间窗口（秒）
DEFAULT_DEDUPLICATION_WINDOW = 300  # 5分钟

# 默认重试次数
DEFAULT_MAX_RETRY_COUNT = 3

# 默认渠道优先级
DEFAULT_CHANNEL_PRIORITY = 5

# 默认消息最大长度
DEFAULT_MAX_MESSAGE_LENGTH = 1000

# ============================================================================
# 事件优先级映射 (Event Priority Mapping)
# ============================================================================

EVENT_PRIORITY_MAPPING = {
    # 紧急事件
    EVENT_SYSTEM_ERROR: NOTIFICATION_PRIORITY_URGENT,
    EVENT_DISK_SPACE_LOW: NOTIFICATION_PRIORITY_URGENT,
    EVENT_SITE_AUTH_EXPIRED: NOTIFICATION_PRIORITY_URGENT,
    EVENT_USER_LOGIN_ANOMALY: NOTIFICATION_PRIORITY_URGENT,

    # 高优先级事件
    EVENT_DOWNLOAD_FAILED: NOTIFICATION_PRIORITY_HIGH,
    EVENT_SITE_CONNECTION_FAILED: NOTIFICATION_PRIORITY_HIGH,
    EVENT_TASK_FAILED: NOTIFICATION_PRIORITY_HIGH,
    EVENT_SUBSCRIPTION_MATCHED: NOTIFICATION_PRIORITY_HIGH,

    # 普通优先级事件
    EVENT_DOWNLOAD_COMPLETED: NOTIFICATION_PRIORITY_NORMAL,
    EVENT_SUBSCRIPTION_DOWNLOADED: NOTIFICATION_PRIORITY_NORMAL,
    EVENT_SUBSCRIPTION_COMPLETED: NOTIFICATION_PRIORITY_NORMAL,
    EVENT_MEDIA_ORGANIZED: NOTIFICATION_PRIORITY_NORMAL,
    EVENT_RESOURCE_FREE_PROMOTION: NOTIFICATION_PRIORITY_NORMAL,

    # 低优先级事件
    EVENT_DOWNLOAD_STARTED: NOTIFICATION_PRIORITY_LOW,
    EVENT_DOWNLOAD_PAUSED: NOTIFICATION_PRIORITY_LOW,
    EVENT_SITE_SYNC_COMPLETED: NOTIFICATION_PRIORITY_LOW,
    EVENT_MEDIA_SCAN_COMPLETED: NOTIFICATION_PRIORITY_LOW,
    EVENT_MEDIA_METADATA_SCRAPED: NOTIFICATION_PRIORITY_LOW,
    EVENT_TASK_COMPLETED: NOTIFICATION_PRIORITY_LOW,
    EVENT_SUBSCRIPTION_NO_RESOURCE: NOTIFICATION_PRIORITY_LOW,
    EVENT_RESOURCE_2X_PROMOTION: NOTIFICATION_PRIORITY_LOW,
    EVENT_RESOURCE_HIGH_QUALITY: NOTIFICATION_PRIORITY_LOW,
    EVENT_SYSTEM_UPDATE_AVAILABLE: NOTIFICATION_PRIORITY_LOW,
}

# ============================================================================
# 默认启用的事件 (Default Enabled Events)
# ============================================================================

DEFAULT_ENABLED_EVENTS = [
    # 订阅相关
    EVENT_SUBSCRIPTION_MATCHED,
    EVENT_SUBSCRIPTION_DOWNLOADED,
    EVENT_SUBSCRIPTION_COMPLETED,
    # 下载相关
    EVENT_DOWNLOAD_COMPLETED,
    EVENT_DOWNLOAD_FAILED,
    # PT站点相关
    EVENT_SITE_CONNECTION_FAILED,
    EVENT_SITE_AUTH_EXPIRED,
    # 系统相关
    EVENT_SYSTEM_ERROR,
    EVENT_DISK_SPACE_LOW,
    EVENT_USER_LOGIN_ANOMALY,
]
