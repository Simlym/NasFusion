# -*- coding: utf-8 -*-
"""
媒体目录相关常量定义
"""

# ==================== 问题类型 ====================
ISSUE_TYPE_MISSING_POSTER = "missing_poster"  # 缺少海报
ISSUE_TYPE_MISSING_NFO = "missing_nfo"  # 缺少NFO
ISSUE_TYPE_UNIDENTIFIED = "unidentified"  # 未识别
ISSUE_TYPE_DUPLICATE = "duplicate"  # 重复文件
ISSUE_TYPE_MISSING_FILES = "missing_files"  # 缺少文件（目录存在但无媒体文件）

ISSUE_TYPES = [
    ISSUE_TYPE_MISSING_POSTER,
    ISSUE_TYPE_MISSING_NFO,
    ISSUE_TYPE_UNIDENTIFIED,
    ISSUE_TYPE_DUPLICATE,
    ISSUE_TYPE_MISSING_FILES,
]

ISSUE_TYPE_DISPLAY_NAMES = {
    ISSUE_TYPE_MISSING_POSTER: "缺少海报",
    ISSUE_TYPE_MISSING_NFO: "缺少NFO",
    ISSUE_TYPE_UNIDENTIFIED: "未识别",
    ISSUE_TYPE_DUPLICATE: "重复文件",
    ISSUE_TYPE_MISSING_FILES: "缺少文件",
}

# ==================== 扫描模式 ====================
SCAN_MODE_FULL = "full"  # 全量扫描（重建所有数据）
SCAN_MODE_INCREMENTAL = "incremental"  # 增量扫描（仅检测变更）

SCAN_MODES = [
    SCAN_MODE_FULL,
    SCAN_MODE_INCREMENTAL,
]

SCAN_MODE_DISPLAY_NAMES = {
    SCAN_MODE_FULL: "全量扫描",
    SCAN_MODE_INCREMENTAL: "增量扫描",
}
