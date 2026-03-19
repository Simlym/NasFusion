# -*- coding: utf-8 -*-
"""
下载器相关常量定义
"""

# ==================== 下载器类型 ====================
DOWNLOADER_TYPE_QBITTORRENT = "qbittorrent"
DOWNLOADER_TYPE_TRANSMISSION = "transmission"
DOWNLOADER_TYPE_SYNOLOGY_DS = "synology_ds"

DOWNLOADER_TYPES = [
    DOWNLOADER_TYPE_QBITTORRENT,
    DOWNLOADER_TYPE_TRANSMISSION,
    DOWNLOADER_TYPE_SYNOLOGY_DS,
]

DOWNLOADER_TYPE_DISPLAY_NAMES = {
    DOWNLOADER_TYPE_QBITTORRENT: "qBittorrent",
    DOWNLOADER_TYPE_TRANSMISSION: "Transmission",
    DOWNLOADER_TYPE_SYNOLOGY_DS: "Synology Download Station",
}

# ==================== 下载任务状态 ====================
TASK_STATUS_PENDING = "pending"  # 等待下载
TASK_STATUS_DOWNLOADING = "downloading"  # 下载中
TASK_STATUS_PAUSED = "paused"  # 已暂停
TASK_STATUS_COMPLETED = "completed"  # 下载完成
TASK_STATUS_SEEDING = "seeding"  # 做种中
TASK_STATUS_ERROR = "error"  # 错误
TASK_STATUS_DELETED = "deleted"  # 已删除

TASK_STATUSES = [
    TASK_STATUS_PENDING,
    TASK_STATUS_DOWNLOADING,
    TASK_STATUS_PAUSED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_SEEDING,
    TASK_STATUS_ERROR,
    TASK_STATUS_DELETED,
]

TASK_STATUS_DISPLAY_NAMES = {
    TASK_STATUS_PENDING: "等待下载",
    TASK_STATUS_DOWNLOADING: "下载中",
    TASK_STATUS_PAUSED: "已暂停",
    TASK_STATUS_COMPLETED: "下载完成",
    TASK_STATUS_SEEDING: "做种中",
    TASK_STATUS_ERROR: "错误",
    TASK_STATUS_DELETED: "已删除",
}

# ==================== 下载器状态 ====================
DOWNLOADER_STATUS_ONLINE = "online"  # 在线
DOWNLOADER_STATUS_OFFLINE = "offline"  # 离线
DOWNLOADER_STATUS_ERROR = "error"  # 错误

DOWNLOADER_STATUSES = [
    DOWNLOADER_STATUS_ONLINE,
    DOWNLOADER_STATUS_OFFLINE,
    DOWNLOADER_STATUS_ERROR,
]

# ==================== HR处理策略 ====================
HR_STRATEGY_NONE = "none"  # 不处理
HR_STRATEGY_AUTO_LIMIT = "auto_limit"  # 自动设置做种限制
HR_STRATEGY_MANUAL = "manual"  # 手动处理

HR_STRATEGIES = [
    HR_STRATEGY_NONE,
    HR_STRATEGY_AUTO_LIMIT,
    HR_STRATEGY_MANUAL,
]

HR_STRATEGY_DISPLAY_NAMES = {
    HR_STRATEGY_NONE: "不处理",
    HR_STRATEGY_AUTO_LIMIT: "自动设置做种限制",
    HR_STRATEGY_MANUAL: "手动处理",
}
