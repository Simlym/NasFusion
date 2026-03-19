# -*- coding: utf-8 -*-
"""
PT站点相关常量

包括站点状态、类型、能力等定义
"""

# ========== 站点状态 ==========

# 站点状态
SITE_STATUS_ACTIVE = "active"
SITE_STATUS_INACTIVE = "inactive"
SITE_STATUS_ERROR = "error"

SITE_STATUSES = [
    SITE_STATUS_ACTIVE,
    SITE_STATUS_INACTIVE,
    SITE_STATUS_ERROR,
]

# 健康状态
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_UNHEALTHY = "unhealthy"

HEALTH_STATUSES = [
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_UNHEALTHY,
]

# ========== 站点类型 ==========

# 站点类型（对应适配器）
# API站点
SITE_TYPE_MTEAM = "mteam"

# NexusPHP站点（网页解析）
SITE_TYPE_NEXUSPHP = "nexusphp"  # 通用NexusPHP适配器
SITE_TYPE_HDSKY = "hdsky"        # 天空
SITE_TYPE_CHDBITS = "chdbits"    # 彩虹岛
SITE_TYPE_PTHOME = "pthome"      # 铂金家
SITE_TYPE_OURBITS = "ourbits"    # 我堡
SITE_TYPE_HDCHINA = "hdchina"    # 瓷器

SITE_TYPES = [
    SITE_TYPE_MTEAM,
    SITE_TYPE_NEXUSPHP,
    SITE_TYPE_HDSKY,
    SITE_TYPE_CHDBITS,
    SITE_TYPE_PTHOME,
    SITE_TYPE_OURBITS,
    SITE_TYPE_HDCHINA,
]

# 站点类型显示名称
SITE_TYPE_DISPLAY_NAMES = {
    SITE_TYPE_MTEAM: "馒头 (API)",
    SITE_TYPE_NEXUSPHP: "NexusPHP通用",
    SITE_TYPE_HDSKY: "天空",
    SITE_TYPE_CHDBITS: "彩虹岛",
    SITE_TYPE_PTHOME: "铂金家",
    SITE_TYPE_OURBITS: "我堡",
    SITE_TYPE_HDCHINA: "瓷器",
}

# ========== 站点能力类型 ==========

# 时间过滤能力
CAPABILITY_TIME_FILTER = "supports_time_filter"

# 成人模式能力
CAPABILITY_ADULT_MODE = "supports_adult_mode"

# 分类过滤能力
CAPABILITY_CATEGORY_FILTER = "supports_category_filter"

# 关键字搜索能力
CAPABILITY_KEYWORD_SEARCH = "supports_keyword_search"

# 高级搜索能力（分辨率、编码、来源等）
CAPABILITY_ADVANCED_SEARCH = "supports_advanced_search"

# 促销过滤能力
CAPABILITY_PROMOTION_FILTER = "supports_promotion_filter"

# 排序能力
CAPABILITY_SORTING = "supports_sorting"

# 所有能力列表
ALL_CAPABILITIES = [
    CAPABILITY_TIME_FILTER,
    CAPABILITY_ADULT_MODE,
    CAPABILITY_CATEGORY_FILTER,
    CAPABILITY_KEYWORD_SEARCH,
    CAPABILITY_ADVANCED_SEARCH,
    CAPABILITY_PROMOTION_FILTER,
    CAPABILITY_SORTING,
]

# 能力显示名称
CAPABILITY_DISPLAY_NAMES = {
    CAPABILITY_TIME_FILTER: "时间范围过滤",
    CAPABILITY_ADULT_MODE: "成人模式切换",
    CAPABILITY_CATEGORY_FILTER: "分类过滤",
    CAPABILITY_KEYWORD_SEARCH: "关键字搜索",
    CAPABILITY_ADVANCED_SEARCH: "高级搜索",
    CAPABILITY_PROMOTION_FILTER: "促销过滤",
    CAPABILITY_SORTING: "排序支持",
}

# ========== MTeam 站点默认能力 ==========

MTEAM_DEFAULT_CAPABILITIES = {
    CAPABILITY_TIME_FILTER: True,
    CAPABILITY_ADULT_MODE: True,
    CAPABILITY_CATEGORY_FILTER: True,
    CAPABILITY_KEYWORD_SEARCH: True,
    CAPABILITY_ADVANCED_SEARCH: False,  # 未来扩展
    CAPABILITY_PROMOTION_FILTER: False,  # 未来扩展
    CAPABILITY_SORTING: True,
}

# ========== 同步过滤参数模式 ==========

# 资源模式
SYNC_MODE_NORMAL = "normal"    # 普通资源（包含所有非成人资源）
SYNC_MODE_MOVIE = "movie"      # 电影资源
SYNC_MODE_TVSHOW = "tvshow"    # 电视剧资源
SYNC_MODE_ADULT = "adult"      # 成人资源

SYNC_MODES = [
    SYNC_MODE_NORMAL,
    SYNC_MODE_MOVIE,
    SYNC_MODE_TVSHOW,
    SYNC_MODE_ADULT,
]

SYNC_MODE_DISPLAY_NAMES = {
    SYNC_MODE_NORMAL: "普通模式",
    SYNC_MODE_MOVIE: "电影模式",
    SYNC_MODE_TVSHOW: "电视模式",
    SYNC_MODE_ADULT: "成人模式",
}
