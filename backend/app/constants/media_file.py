# -*- coding: utf-8 -*-
"""
媒体文件相关常量定义
"""

# ==================== 媒体文件类型 ====================
FILE_TYPE_VIDEO = "video"
FILE_TYPE_AUDIO = "audio"
FILE_TYPE_SUBTITLE = "subtitle"
FILE_TYPE_OTHER = "other"

FILE_TYPES = [
    FILE_TYPE_VIDEO,
    FILE_TYPE_AUDIO,
    FILE_TYPE_SUBTITLE,
    FILE_TYPE_OTHER,
]

FILE_TYPE_DISPLAY_NAMES = {
    FILE_TYPE_VIDEO: "视频",
    FILE_TYPE_AUDIO: "音频",
    FILE_TYPE_SUBTITLE: "字幕",
    FILE_TYPE_OTHER: "其他",
}

# ==================== 视频文件扩展名 ====================
VIDEO_EXTENSIONS = [
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".rmvb", ".iso"
]

# ==================== 音频文件扩展名 ====================
AUDIO_EXTENSIONS = [
    ".mp3", ".flac", ".wav", ".aac", ".m4a", ".wma", ".ogg",
    ".ape", ".alac", ".dts", ".ac3", ".eac3"
]

# ==================== 字幕文件扩展名 ====================
SUBTITLE_EXTENSIONS = [
    ".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt", ".sup"
]

# ==================== 媒体文件状态 ====================
MEDIA_FILE_STATUS_DISCOVERED = "discovered"  # 已发现
MEDIA_FILE_STATUS_IDENTIFYING = "identifying"  # 识别中
MEDIA_FILE_STATUS_IDENTIFIED = "identified"  # 已识别
MEDIA_FILE_STATUS_ORGANIZING = "organizing"  # 整理中
MEDIA_FILE_STATUS_SCRAPING = "scraping"  # 刮削中（获取元数据）
MEDIA_FILE_STATUS_COMPLETED = "completed"  # 已完成
MEDIA_FILE_STATUS_FAILED = "failed"  # 失败
MEDIA_FILE_STATUS_IGNORED = "ignored"  # 已忽略
MEDIA_FILE_STATUS_DELETED = "deleted"  # 已删除（文件不存在）

MEDIA_FILE_STATUSES = [
    MEDIA_FILE_STATUS_DISCOVERED,
    MEDIA_FILE_STATUS_IDENTIFYING,
    MEDIA_FILE_STATUS_IDENTIFIED,
    MEDIA_FILE_STATUS_ORGANIZING,
    MEDIA_FILE_STATUS_SCRAPING,
    MEDIA_FILE_STATUS_COMPLETED,
    MEDIA_FILE_STATUS_FAILED,
    MEDIA_FILE_STATUS_IGNORED,
    MEDIA_FILE_STATUS_DELETED,
]

MEDIA_FILE_STATUS_DISPLAY_NAMES = {
    MEDIA_FILE_STATUS_DISCOVERED: "已发现",
    MEDIA_FILE_STATUS_IDENTIFYING: "识别中",
    MEDIA_FILE_STATUS_IDENTIFIED: "已识别",
    MEDIA_FILE_STATUS_ORGANIZING: "整理中",
    MEDIA_FILE_STATUS_SCRAPING: "刮削中",
    MEDIA_FILE_STATUS_COMPLETED: "已完成",
    MEDIA_FILE_STATUS_FAILED: "失败",
    MEDIA_FILE_STATUS_IGNORED: "已忽略",
    MEDIA_FILE_STATUS_DELETED: "已删除",
}

# ==================== 文件匹配方法 ====================
MATCH_METHOD_FROM_DOWNLOAD = "from_download"  # 从下载任务关联
MATCH_METHOD_FROM_PT_TITLE = "from_pt_title"  # 从PT资源标题匹配
MATCH_METHOD_FROM_FILENAME = "from_filename"  # 从文件名解析
MATCH_METHOD_FROM_MEDIAINFO = "from_mediainfo"  # 从MediaInfo分析
MATCH_METHOD_MANUAL = "manual"  # 手动指定
MATCH_METHOD_FROM_NFO = "from_nfo"  # 从NFO文件识别
MATCH_METHOD_NONE = "none"  # 未匹配

MATCH_METHODS = [
    MATCH_METHOD_FROM_DOWNLOAD,
    MATCH_METHOD_FROM_PT_TITLE,
    MATCH_METHOD_FROM_FILENAME,
    MATCH_METHOD_FROM_MEDIAINFO,
    MATCH_METHOD_MANUAL,
    MATCH_METHOD_FROM_NFO,
    MATCH_METHOD_NONE,
]

MATCH_METHOD_DISPLAY_NAMES = {
    MATCH_METHOD_FROM_DOWNLOAD: "下载任务关联",
    MATCH_METHOD_FROM_PT_TITLE: "PT标题匹配",
    MATCH_METHOD_FROM_FILENAME: "文件名解析",
    MATCH_METHOD_FROM_MEDIAINFO: "MediaInfo分析",
    MATCH_METHOD_MANUAL: "手动指定",
    MATCH_METHOD_FROM_NFO: "NFO文件识别",
    MATCH_METHOD_NONE: "未匹配",
}

# ==================== 文件整理模式 ====================
ORGANIZE_MODE_HARDLINK = "hardlink"  # 硬链接（推荐，节省空间且不影响做种）
ORGANIZE_MODE_REFLINK = "reflink"  # Reflink（CoW克隆，Btrfs推荐，可跨共享目录）
ORGANIZE_MODE_SYMLINK = "symlink"  # 软链接（符号链接）
ORGANIZE_MODE_MOVE = "move"  # 移动文件
ORGANIZE_MODE_COPY = "copy"  # 复制文件

ORGANIZE_MODES = [
    ORGANIZE_MODE_HARDLINK,
    ORGANIZE_MODE_REFLINK,
    ORGANIZE_MODE_SYMLINK,
    ORGANIZE_MODE_MOVE,
    ORGANIZE_MODE_COPY,
]

ORGANIZE_MODE_DISPLAY_NAMES = {
    ORGANIZE_MODE_HARDLINK: "硬链接（推荐）",
    ORGANIZE_MODE_REFLINK: "Reflink（Btrfs推荐）",
    ORGANIZE_MODE_SYMLINK: "软链接",
    ORGANIZE_MODE_MOVE: "移动文件",
    ORGANIZE_MODE_COPY: "复制文件",
}

# ==================== NFO格式类型 ====================
NFO_FORMAT_JELLYFIN = "jellyfin"  # Jellyfin格式（也兼容Emby）
NFO_FORMAT_EMBY = "emby"  # Emby格式（与Jellyfin基本相同）
NFO_FORMAT_PLEX = "plex"  # Plex格式
NFO_FORMAT_KODI = "kodi"  # Kodi格式

NFO_FORMATS = [
    NFO_FORMAT_JELLYFIN,
    NFO_FORMAT_EMBY,
    NFO_FORMAT_PLEX,
    NFO_FORMAT_KODI,
]

NFO_FORMAT_DISPLAY_NAMES = {
    NFO_FORMAT_JELLYFIN: "Jellyfin",
    NFO_FORMAT_EMBY: "Emby",
    NFO_FORMAT_PLEX: "Plex",
    NFO_FORMAT_KODI: "Kodi",
}

# ==================== 统一资源表名常量 ====================
UNIFIED_TABLE_MOVIES = "unified_movies"
UNIFIED_TABLE_TV = "unified_tv_series"
UNIFIED_TABLE_MUSIC = "unified_music"
UNIFIED_TABLE_BOOKS = "unified_books"
UNIFIED_TABLE_ANIME = "unified_anime"
UNIFIED_TABLE_ADULT = "unified_adult"

UNIFIED_TABLES = [
    UNIFIED_TABLE_MOVIES,
    UNIFIED_TABLE_TV,
    UNIFIED_TABLE_MUSIC,
    UNIFIED_TABLE_BOOKS,
    UNIFIED_TABLE_ANIME,
    UNIFIED_TABLE_ADULT,
]

# ==================== 默认目录结构模板 ====================
# 电影：/media/Movies/电影名称 (年份)/电影名称 (年份).mkv
DEFAULT_MOVIE_DIR_TEMPLATE = "{title} ({year})"
DEFAULT_MOVIE_FILENAME_TEMPLATE = "{title} ({year})"

# 电视剧：/media/TV Shows/剧集名称 (年份)/Season 1/剧集名称 - S01E01 - 集标题.mkv
# 匹配 TinyMediaManager 命名规则
DEFAULT_TV_DIR_TEMPLATE = "{title} ({year})/Season {season}"
DEFAULT_TV_FILENAME_TEMPLATE = "{title} - S{season:02d}E{episode:02d} - {episode_title}"

# 动漫：/media/Anime/动漫名称 (年份)/Season 1/动漫名称 - S01E01 - 集标题.mkv
# 匹配 TinyMediaManager 命名规则
DEFAULT_ANIME_DIR_TEMPLATE = "{title} ({year})/Season {season}"
DEFAULT_ANIME_FILENAME_TEMPLATE = "{title} - S{season:02d}E{episode:02d} - {episode_title}"

# 电子书：/media/Books/书名/书名.扩展名
DEFAULT_BOOK_DIR_TEMPLATE = "{title}"
DEFAULT_BOOK_FILENAME_TEMPLATE = "{title}"

# 音乐：/media/Music/艺术家/专辑名/歌曲名.扩展名
DEFAULT_MUSIC_DIR_TEMPLATE = "{artist}/{album}"
DEFAULT_MUSIC_FILENAME_TEMPLATE = "{track:02d} - {title}"

# 成人内容：/media/Adult/标题 (年份)/标题 (年份).扩展名
DEFAULT_ADULT_DIR_TEMPLATE = "{title} ({year})"
DEFAULT_ADULT_FILENAME_TEMPLATE = "{title} ({year})"
