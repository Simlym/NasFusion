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
SITE_SCHEMA_UNIT3D = "unit3d"  # Unit3D框架（国际站，网页解析）
SITE_SCHEMA_GAZELLE = "gazelle"  # Gazelle框架（音乐站）
SITE_SCHEMA_GENERIC_JSON_API = "generic_json_api"  # 通用JSON API（TNode/Yema等）

SITE_SCHEMAS = [
    SITE_SCHEMA_NEXUSPHP,
    SITE_SCHEMA_MTEAM,
    SITE_SCHEMA_UNIT3D,
    SITE_SCHEMA_GAZELLE,
    SITE_SCHEMA_GENERIC_JSON_API,
]

# ==================== 共享配置（供 NexusPHP 站点复用）====================
#
# 标准 NexusPHP 分类 ID(401-409) -> 媒体类型映射。
# 绝大多数国内 NexusPHP 站沿用这套约定俗成的分类编号，新增站点直接复用此表。
# 若某站分类与此不同（异形站），在该站 preset 里单独写 category_details 覆盖即可。
# 注：分类“名称/映射”后续可通过“同步站点分类”从真站拉取并自动纠正。
STANDARD_NEXUSPHP_CATEGORY_DETAILS: Dict[str, Dict[str, Any]] = {
    "401": {"name_chs": "电影", "name_eng": "Movies", "mapped_category": MEDIA_TYPE_MOVIE},
    "402": {"name_chs": "剧集", "name_eng": "TV Series", "mapped_category": MEDIA_TYPE_TV},
    "403": {"name_chs": "综艺", "name_eng": "TV Shows", "mapped_category": MEDIA_TYPE_OTHER},
    "404": {"name_chs": "纪录片", "name_eng": "Documentaries", "mapped_category": MEDIA_TYPE_OTHER},
    "405": {"name_chs": "动漫", "name_eng": "Animations", "mapped_category": MEDIA_TYPE_ANIME},
    "406": {"name_chs": "音乐MV", "name_eng": "Music Videos", "mapped_category": MEDIA_TYPE_MUSIC},
    "407": {"name_chs": "体育", "name_eng": "Sports", "mapped_category": MEDIA_TYPE_OTHER},
    "408": {"name_chs": "音乐", "name_eng": "Music", "mapped_category": MEDIA_TYPE_MUSIC},
    "409": {"name_chs": "其他", "name_eng": "Misc", "mapped_category": MEDIA_TYPE_OTHER},
}

# NexusPHP 站点默认运行参数（限速/同步策略）。新站不写 default_config 时可复用。
STANDARD_NEXUSPHP_DEFAULT_CONFIG: Dict[str, Any] = {
    "request_interval": 5,
    "sync_interval": 120,
    "max_requests_per_day": 200,
    "sync_strategy": "page_based",
}

# NexusPHP 站点默认能力。
STANDARD_NEXUSPHP_CAPABILITIES = [
    "category_filter",
    "keyword_search",
    "promotion_filter",
    "sorting",
]


def _nexusphp_preset(
    display_name: str,
    domain: str,
    description: str = "",
    *,
    base_url: str | None = None,
    icon: str | None = None,
) -> Dict[str, Any]:
    """构造一个标准 NexusPHP 站点预设。

    复用标准分类(401-409)、默认运行参数与能力；不写 nexusphp_config，
    由 NexusPHPAdapter 内置默认选择器(_get_default_selectors)兜底。
    异形站点请直接手写完整 preset，不要用此辅助函数。
    """
    return {
        "display_name": display_name,
        "domain": domain,
        "base_url": base_url or f"https://{domain}",
        "schema": SITE_SCHEMA_NEXUSPHP,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie", "passkey"],
        "description": description,
        "icon": icon,  # 预留：站点 logo 文件名；前端当前用文字短名兜底
        "timezone": "Asia/Shanghai",
        "category_details": STANDARD_NEXUSPHP_CATEGORY_DETAILS,
        "default_config": STANDARD_NEXUSPHP_DEFAULT_CONFIG,
        "capabilities": STANDARD_NEXUSPHP_CAPABILITIES,
    }


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

    # ==================== 主流国内 NexusPHP 站点（复用通用默认）====================
    # 以下站点均为标准 NexusPHP 框架，复用标准分类(401-409)与适配器内置默认选择器，
    # 不写 nexusphp_config。若某站为异形（分类/选择器特殊），改写为完整 preset 覆盖即可。
    # 域名以各站常用主域为准；用户也可在“高级选项”里覆盖 domain/base_url。
    # 添加站点后建议先“同步站点分类”，从真站拉取真实分类名称并自动纠正映射。
    "hdhome": _nexusphp_preset("HDHome", "hdhome.org", "瓷器旗下，综合高清资源站"),
    "hdfans": _nexusphp_preset("HDFans", "hdfans.org", "综合资源站"),
    "btschool": _nexusphp_preset("学校", "pt.btschool.club", "BTSCHOOL，老牌综合站"),
    "hdtime": _nexusphp_preset("HDTime", "hdtime.org", "综合资源站"),
    "hdarea": _nexusphp_preset("高清地带", "hdarea.co", "HDArea，综合高清站"),
    "soulvoice": _nexusphp_preset("聆音", "pt.soulvoice.club", "音乐及综合资源站"),
    "ptsbao": _nexusphp_preset("烧包", "ptsbao.club", "高码率发烧资源站"),
    "hddolby": _nexusphp_preset("杜比", "www.hddolby.com", "HDDolby，高清综合站"),
    "audiences": _nexusphp_preset("观众", "audiences.me", "Audiences，综合资源站"),
    "hdfun": _nexusphp_preset("飞乐", "hdfun.me", "综合资源站"),
    "tjupt": _nexusphp_preset("北洋园", "tjupt.org", "天津大学 PT，教育网站点"),
    "hdmayi": _nexusphp_preset("蚂蚁", "hdmayi.com", "综合资源站"),
    "carpt": _nexusphp_preset("CarPT", "carpt.net", "汽车及综合资源站"),
    "ptchina": _nexusphp_preset("铂金学院", "ptchina.org", "综合资源站"),
    "hdpt": _nexusphp_preset("好多", "hdpt.xyz", "综合资源站"),
    "1ptba": _nexusphp_preset("一坛", "1ptba.com", "综合资源站"),
    "haidan": _nexusphp_preset("海胆", "www.haidan.video", "影视综合站"),
    "okpt": _nexusphp_preset("OKPT", "www.okpt.net", "综合资源站"),

    # ==================== UNIT3D 站点（国际，网页解析）====================
    # 示例：Blutopia（BLU）。同框架新增站点只需复制此项并改 domain/base_url/category_details。
    "blutopia": {
        "display_name": "Blutopia",
        "domain": "blutopia.cc",
        "base_url": "https://blutopia.cc",
        "schema": SITE_SCHEMA_UNIT3D,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie", "passkey"],  # Cookie 网页访问；passkey(rsskey) 用于下载
        "description": "UNIT3D 框架国际综合站，质量优先",
        "icon": "blutopia.png",
        "timezone": "UTC",
        # UNIT3D 分类ID -> 媒体类型（依据站点 /categories）
        "category_details": {
            "1": {"name_chs": "电影", "name_eng": "Movie", "mapped_category": MEDIA_TYPE_MOVIE},
            "2": {"name_chs": "剧集", "name_eng": "TV", "mapped_category": MEDIA_TYPE_TV},
            "3": {"name_chs": "音乐", "name_eng": "Music", "mapped_category": MEDIA_TYPE_MUSIC},
            "4": {"name_chs": "其他", "name_eng": "Other", "mapped_category": MEDIA_TYPE_OTHER},
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
        ],
        # UNIT3D 特有配置（可选；不填则用适配器内置默认选择器）
        "unit3d_config": {
            "torrents_page": "/torrents",
            # selectors 留空表示使用 DEFAULT_UNIT3D_SELECTORS；
            # 异形站点可在此覆盖单个选择器。
        },
    },

    # ==================== Generic JSON API 站点 ====================
    # 示例：TNode。规整 JSON-API 站点仅需此配置，无需写 Python 代码。
    "tnode": {
        "display_name": "TNode",
        "domain": "tnode.club",
        "base_url": "https://tnode.club",
        "schema": SITE_SCHEMA_GENERIC_JSON_API,
        "auth_type": AUTH_TYPE_COOKIE,
        "auth_fields": ["cookie"],
        "description": "TNode JSON API 站点",
        "icon": "tnode.png",
        "timezone": "Asia/Shanghai",
        "category_details": {
            "501": {"name_chs": "电影", "name_eng": "Movie", "mapped_category": MEDIA_TYPE_MOVIE},
            "502": {"name_chs": "剧集", "name_eng": "TV", "mapped_category": MEDIA_TYPE_TV},
            "503": {"name_chs": "综艺", "name_eng": "Show", "mapped_category": MEDIA_TYPE_OTHER},
            "504": {"name_chs": "动漫", "name_eng": "Anime", "mapped_category": MEDIA_TYPE_ANIME},
        },
        "default_config": {
            "request_interval": 3,
            "sync_interval": 120,
            "max_requests_per_day": 300,
            "sync_strategy": "page_based",
        },
        "capabilities": [
            "category_filter",
            "keyword_search",
        ],
        # 配置驱动的 JSON-API 定义
        "api_config": {
            # 需要先获取页面里的 CSRF token
            "csrf": {
                "enabled": True,
                "token_url": "/",
                "regex": r'<meta name="x-csrf-token" content="(.+?)">',
                "header": "X-CSRF-TOKEN",
            },
            "search": {
                "url": "/api/torrent/advancedSearch",
                "method": "POST",
                "page_base": 1,  # 接口页码从 1 开始
                "body": {
                    "page": "{{page}}",
                    "size": "{{size}}",
                    "type": "title",
                    "keyword": "{{keyword}}",
                    "sorter": "id",
                    "order": "desc",
                    "tags": [],
                    "category": [501, 502, 503, 504],
                    "medium": [],
                    "videoCoding": [],
                    "audioCoding": [],
                    "resolution": [],
                    "group": [],
                },
            },
            "response": {
                "list_path": "data.torrents",
                "total_path": "data.total",
                "page_size": 100,
            },
            # 标准字段 -> 原始 JSON 点号路径
            "field_mapping": {
                "torrent_id": "id",
                "title": "title",
                "subtitle": "subtitle",
                "size_bytes": "size",
                "seeders": "seeding",
                "leechers": "leeching",
                "completions": "complete",
                "original_category_id": "category",
                "imdb_id": "imdb",
            },
            "time_fields": {
                "published_at": {"field": "upload_time", "format": "timestamp"},
            },
            # 促销：下载/上传系数
            "promotion": {
                "type": "factor",
                "download_factor_field": "downloadRate",
                "upload_factor_field": "uploadRate",
            },
            "download_url": "/api/torrent/download/{{torrent_id}}",
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
    "SITE_SCHEMA_GENERIC_JSON_API",
    "SITE_SCHEMAS",
    "SITE_PRESETS",
    "get_site_preset",
    "get_all_presets",
    "get_preset_list",
]
