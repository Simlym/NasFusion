# -*- coding: utf-8 -*-
"""
站点预设配置

定义各PT站点的默认配置，用户添加站点时只需选择站点并填写认证信息
"""

from typing import Dict, Any

from app.constants.auth import AUTH_TYPE_COOKIE, AUTH_TYPE_PASSKEY
from app.constants.media import (
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TV,
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_OTHER,
)

# 站点框架类型
SITE_SCHEMA_NEXUSPHP = "nexusphp"  # NexusPHP框架（国内大多数PT站）
SITE_SCHEMA_MTEAM = "mteam"  # MTeam（使用API）
SITE_SCHEMA_UNIT3D = "unit3d"  # Unit3D框架
SITE_SCHEMA_GAZELLE = "gazelle"  # Gazelle框架（音乐站）

SITE_SCHEMAS = [
    SITE_SCHEMA_NEXUSPHP,
    SITE_SCHEMA_MTEAM,
    SITE_SCHEMA_UNIT3D,
    SITE_SCHEMA_GAZELLE,
]

# 站点预设配置
# 每个站点包含：display_name, domain, base_url, schema, auth_type, categories, default_config
#
# 分类配置说明：
# - MTeam 等有API的站点：使用 categories（简单映射格式 {分类ID: 媒体类型}），分类详情通过API获取
# - NexusPHP 等无API的站点：使用 category_details（完整格式），包含分类名称和映射关系
SITE_PRESETS: Dict[str, Dict[str, Any]] = {
    # ==================== MTeam（API站点）====================
    # MTeam 有API接口，分类通过接口获取，无需预设 category_details
    "mteam": {
        "display_name": "馒头",
        "domain": "kp.m-team.cc",
        "base_url": "https://api.m-team.cc",
        "schema": SITE_SCHEMA_MTEAM,
        "auth_type": AUTH_TYPE_PASSKEY,
        "auth_fields": ["passkey"],  # 需要用户填写的认证字段
        "description": "综合PT站，API接口完善，资源丰富",
        "icon": "mteam.png",
        "timezone": "Asia/Shanghai",
        "categories": {
            "401": MEDIA_TYPE_MOVIE,
            "402": MEDIA_TYPE_TV,  # 剧集
            "403": MEDIA_TYPE_TV,
            "404": MEDIA_TYPE_TV,  # 综艺
            "405": MEDIA_TYPE_ANIME,
            "406": MEDIA_TYPE_MUSIC,
            "407": MEDIA_TYPE_OTHER,  # 体育
            "408": MEDIA_TYPE_OTHER,  # 软件
            "409": MEDIA_TYPE_OTHER,  # 学习
            "410": MEDIA_TYPE_OTHER,  # 纪录
        },
        "default_config": {
            "request_interval": 2,
            "sync_interval": 60,
            "max_requests_per_day": 500,
            "sync_strategy": "time_based",
        },
        "capabilities": [
            "time_filter",
            "adult_mode",
            "category_filter",
            "keyword_search",
            "advanced_search",
            "promotion_filter",
            "sorting",
        ],
    },

    # ==================== NexusPHP 站点 ====================
    "hdsky": {
        "display_name": "天空",
        "domain": "hdsky.me",
        "base_url": "https://hdsky.me",
        "schema": SITE_SCHEMA_NEXUSPHP,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie", "passkey"],  # Cookie用于网页访问，Passkey用于下载
        "description": "高清发烧友后花园，综合资源站",
        "icon": "hdsky.png",
        "timezone": "Asia/Shanghai",
        "category_details": {
            "401": {"name_chs": "电影", "name_eng": "Movies", "mapped_category": MEDIA_TYPE_MOVIE},
            "402": {"name_chs": "剧集(分集)", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "403": {"name_chs": "综艺", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_OTHER},
            "404": {"name_chs": "纪录片", "name_eng": "Documentaries", "mapped_category": MEDIA_TYPE_OTHER},
            "405": {"name_chs": "动漫", "name_eng": "Animations", "mapped_category": MEDIA_TYPE_ANIME},
            "406": {"name_chs": "音乐MV", "name_eng": "Music Videos", "mapped_category": MEDIA_TYPE_MUSIC},
            "407": {"name_chs": "体育", "name_eng": "Sports", "mapped_category": MEDIA_TYPE_OTHER},
            "408": {"name_chs": "无损音乐", "name_eng": "HQ Audio", "mapped_category": MEDIA_TYPE_MUSIC},
            "409": {"name_chs": "其他", "name_eng": "Misc", "mapped_category": MEDIA_TYPE_OTHER},
            "410": {"name_chs": "iPad影视", "name_eng": "iPad", "mapped_category": MEDIA_TYPE_MOVIE},
            "411": {"name_chs": "剧集(合集)", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "412": {"name_chs": "海外剧集(分集)", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "413": {"name_chs": "海外剧集(合集)", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "414": {"name_chs": "海外综艺(分集)", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_OTHER},
            "415": {"name_chs": "海外综艺(合集)", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_OTHER},
            "416": {"name_chs": "短剧", "name_eng": "Shortplay", "mapped_category": MEDIA_TYPE_TV},
        },
        "default_config": {
            "request_interval": 5,
            "sync_interval": 120,
            "max_requests_per_day": 200,
            "sync_strategy": "page_based",
        },
        "capabilities": [
            "category_filter",
            "keyword_search",
            "promotion_filter",
            "sorting",
        ],
        "sorting_options": [
            {"value": "1", "label": "标题"},
            {"value": "2", "label": "评论数"},
            {"value": "3", "label": "存活时间"},
            {"value": "4", "label": "大小"},
            {"value": "5", "label": "种子数"},
            {"value": "6", "label": "下载数"},
            {"value": "7", "label": "完成数"},
        ],
        # NexusPHP站点特有配置
        "nexusphp_config": {
            "torrents_page": "/torrents.php",
            "details_page": "/details.php",
            "download_page": "/download.php",
            "search_params": {
                "search": "{keyword}",
                "cat": "{category}",
                "page": "{page}",
            },
            # 页面选择器配置
            "selectors": {
                "torrent_table": "table.torrents",
                "torrent_row": "tr:not(:first-child)",
                "title": "a[href*='details.php']",
                "subtitle": "td.embedded > span",
                "category": "td:first-child a[href*='cat='] img",
                "size": "td:nth-child(5)",
                "seeders": "td:nth-child(6)",
                "leechers": "td:nth-child(7)",
                "completions": "td:nth-child(8)",
                "published_at": "td:nth-child(4) > span",
                "download_link": "a[href*='download.php']",
                # 促销标识
                "free": "img.pro_free, img.pro_free2up",
                "double_up": "img.pro_2up, img.pro_free2up",
                "half_down": "img.pro_50pctdown",
            },
        },
    },

    "chdbits": {
        "display_name": "彩虹岛",
        "domain": "chdbits.co",
        "base_url": "https://chdbits.co",
        "schema": SITE_SCHEMA_NEXUSPHP,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie", "passkey"],
        "description": "高清资源站，注重质量",
        "icon": "chdbits.png",
        "timezone": "Asia/Shanghai",
        "category_details": {
            "401": {"name_chs": "电影", "name_eng": "Movies", "mapped_category": MEDIA_TYPE_MOVIE},
            "402": {"name_chs": "剧集", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "403": {"name_chs": "综艺", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_TV},
            "404": {"name_chs": "纪录片", "name_eng": "Documentaries", "mapped_category": MEDIA_TYPE_TV},
            "405": {"name_chs": "动漫", "name_eng": "Animations", "mapped_category": MEDIA_TYPE_ANIME},
            "406": {"name_chs": "音乐", "name_eng": "Music", "mapped_category": MEDIA_TYPE_MUSIC},
            "407": {"name_chs": "其他", "name_eng": "Other", "mapped_category": MEDIA_TYPE_OTHER},
        },
        "default_config": {
            "request_interval": 5,
            "sync_interval": 120,
            "max_requests_per_day": 200,
            "sync_strategy": "page_based",
        },
        "capabilities": [
            "category_filter",
            "keyword_search",
            "sorting",
        ],
        "sorting_options": [
            {"value": "1", "label": "标题"},
            {"value": "2", "label": "评论数"},
            {"value": "3", "label": "存活时间"},
            {"value": "4", "label": "大小"},
            {"value": "5", "label": "种子数"},
            {"value": "6", "label": "下载数"},
            {"value": "7", "label": "完成数"},
        ],
        "nexusphp_config": {
            "torrents_page": "/torrents.php",
            "details_page": "/details.php",
            "download_page": "/download.php",
            "search_params": {
                "search": "{keyword}",
                "cat": "{category}",
                "page": "{page}",
            },
            "selectors": {
                "torrent_table": "table.torrents",
                "torrent_row": "tr:not(:first-child)",
                "title": "a[href*='details.php']",
                "subtitle": "td.embedded > span",
                "category": "td:first-child a[href*='cat='] img",
                "size": "td:nth-child(5)",
                "seeders": "td:nth-child(6)",
                "leechers": "td:nth-child(7)",
                "completions": "td:nth-child(8)",
                "published_at": "td:nth-child(4) > span",
                "download_link": "a[href*='download.php']",
                "free": "img.pro_free, img.pro_free2up",
                "double_up": "img.pro_2up, img.pro_free2up",
                "half_down": "img.pro_50pctdown",
            },
        },
    },

    "pthome": {
        "display_name": "铂金家",
        "domain": "pthome.net",
        "base_url": "https://pthome.net",
        "schema": SITE_SCHEMA_NEXUSPHP,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie", "passkey"],
        "description": "综合资源站",
        "icon": "pthome.png",
        "timezone": "Asia/Shanghai",
        "category_details": {
            "401": {"name_chs": "电影", "name_eng": "Movies", "mapped_category": MEDIA_TYPE_MOVIE},
            "402": {"name_chs": "剧集", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "403": {"name_chs": "综艺", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_TV},
            "404": {"name_chs": "纪录片", "name_eng": "Documentaries", "mapped_category": MEDIA_TYPE_TV},
            "405": {"name_chs": "动漫", "name_eng": "Animations", "mapped_category": MEDIA_TYPE_ANIME},
            "406": {"name_chs": "音乐", "name_eng": "Music", "mapped_category": MEDIA_TYPE_MUSIC},
            "407": {"name_chs": "其他", "name_eng": "Other", "mapped_category": MEDIA_TYPE_OTHER},
        },
        "default_config": {
            "request_interval": 5,
            "sync_interval": 120,
            "max_requests_per_day": 200,
            "sync_strategy": "page_based",
        },
        "capabilities": [
            "category_filter",
            "keyword_search",
            "sorting",
        ],
        "sorting_options": [
            {"value": "1", "label": "标题"},
            {"value": "2", "label": "评论数"},
            {"value": "3", "label": "存活时间"},
            {"value": "4", "label": "大小"},
            {"value": "5", "label": "种子数"},
            {"value": "6", "label": "下载数"},
            {"value": "7", "label": "完成数"},
        ],
        "nexusphp_config": {
            "torrents_page": "/torrents.php",
            "details_page": "/details.php",
            "download_page": "/download.php",
            "search_params": {
                "search": "{keyword}",
                "cat": "{category}",
                "page": "{page}",
            },
            "selectors": {
                "torrent_table": "table.torrents",
                "torrent_row": "tr:not(:first-child)",
                "title": "a[href*='details.php']",
                "subtitle": "td.embedded > span",
                "category": "td:first-child a[href*='cat='] img",
                "size": "td:nth-child(5)",
                "seeders": "td:nth-child(6)",
                "leechers": "td:nth-child(7)",
                "completions": "td:nth-child(8)",
                "published_at": "td:nth-child(4) > span",
                "download_link": "a[href*='download.php']",
                "free": "img.pro_free, img.pro_free2up",
                "double_up": "img.pro_2up, img.pro_free2up",
                "half_down": "img.pro_50pctdown",
            },
        },
    },

    "ourbits": {
        "display_name": "我堡",
        "domain": "ourbits.club",
        "base_url": "https://ourbits.club",
        "schema": SITE_SCHEMA_NEXUSPHP,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie", "passkey"],
        "description": "综合资源站，新手友好",
        "icon": "ourbits.png",
        "timezone": "Asia/Shanghai",
        "category_details": {
            "401": {"name_chs": "电影", "name_eng": "Movies", "mapped_category": MEDIA_TYPE_MOVIE},
            "402": {"name_chs": "剧集", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
            "403": {"name_chs": "综艺", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_TV},
            "404": {"name_chs": "纪录片", "name_eng": "Documentaries", "mapped_category": MEDIA_TYPE_TV},
            "405": {"name_chs": "动漫", "name_eng": "Animations", "mapped_category": MEDIA_TYPE_ANIME},
            "406": {"name_chs": "音乐", "name_eng": "Music", "mapped_category": MEDIA_TYPE_MUSIC},
            "407": {"name_chs": "体育", "name_eng": "Sports", "mapped_category": MEDIA_TYPE_OTHER},
            "408": {"name_chs": "软件", "name_eng": "Software", "mapped_category": MEDIA_TYPE_OTHER},
            "409": {"name_chs": "学习", "name_eng": "Education", "mapped_category": MEDIA_TYPE_OTHER},
            "410": {"name_chs": "其他", "name_eng": "Other", "mapped_category": MEDIA_TYPE_OTHER},
        },
        "default_config": {
            "request_interval": 5,
            "sync_interval": 120,
            "max_requests_per_day": 200,
            "sync_strategy": "page_based",
        },
        "capabilities": [
            "category_filter",
            "keyword_search",
            "sorting",
        ],
        "sorting_options": [
            {"value": "1", "label": "标题"},
            {"value": "2", "label": "评论数"},
            {"value": "3", "label": "存活时间"},
            {"value": "4", "label": "大小"},
            {"value": "5", "label": "种子数"},
            {"value": "6", "label": "下载数"},
            {"value": "7", "label": "完成数"},
        ],
        "nexusphp_config": {
            "torrents_page": "/torrents.php",
            "details_page": "/details.php",
            "download_page": "/download.php",
            "search_params": {
                "search": "{keyword}",
                "cat": "{category}",
                "page": "{page}",
            },
            "selectors": {
                "torrent_table": "table.torrents",
                "torrent_row": "tr:not(:first-child)",
                "title": "a[href*='details.php']",
                "subtitle": "td.embedded > span",
                "category": "td:first-child a[href*='cat='] img",
                "size": "td:nth-child(5)",
                "seeders": "td:nth-child(6)",
                "leechers": "td:nth-child(7)",
                "completions": "td:nth-child(8)",
                "published_at": "td:nth-child(4) > span",
                "download_link": "a[href*='download.php']",
                "free": "img.pro_free, img.pro_free2up",
                "double_up": "img.pro_2up, img.pro_free2up",
                "half_down": "img.pro_50pctdown",
            },
        },
    },
}


def get_site_preset(preset_id: str) -> Dict[str, Any] | None:
    """
    获取站点预设配置

    Args:
        preset_id: 预设ID（如 hdsky, mteam）

    Returns:
        站点预设配置字典，如果不存在返回None
    """
    return SITE_PRESETS.get(preset_id.lower())


def get_all_presets() -> Dict[str, Dict[str, Any]]:
    """
    获取所有站点预设配置

    Returns:
        所有站点预设配置字典
    """
    return SITE_PRESETS


def get_preset_list() -> list[Dict[str, Any]]:
    """
    获取站点预设列表（用于前端下拉选择）

    Returns:
        站点预设列表，每项包含 id, display_name, description, schema, auth_type
    """
    result = []
    for preset_id, preset in SITE_PRESETS.items():
        result.append({
            "id": preset_id,
            "display_name": preset["display_name"],
            "description": preset.get("description", ""),
            "schema": preset["schema"],
            "auth_type": preset["auth_type"],
            "auth_fields": preset.get("auth_fields", []),
            "domain": preset["domain"],
            "icon": preset.get("icon"),
        })
    return result


__all__ = [
    "SITE_SCHEMA_NEXUSPHP",
    "SITE_SCHEMA_MTEAM",
    "SITE_SCHEMA_UNIT3D",
    "SITE_SCHEMA_GAZELLE",
    "SITE_SCHEMAS",
    "SITE_PRESETS",
    "get_site_preset",
    "get_all_presets",
    "get_preset_list",
]
