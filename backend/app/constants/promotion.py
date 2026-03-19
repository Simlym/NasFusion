"""
促销相关常量
"""

# 促销类型
PROMO_TYPE_FREE = "free"           # 免费下载
PROMO_TYPE_2X_FREE = "2xfree"      # 2倍上传 + 免费下载
PROMO_TYPE_2X_UP = "2x"            # 2倍上传
PROMO_TYPE_50_OFF = "50%"          # 50%下载
PROMO_TYPE_2X_50_OFF = "2x50%"     # 2倍上传 + 50%下载
PROMO_TYPE_30_OFF = "30%"          # 30%下载
PROMO_TYPE_NONE = "none"           # 无促销

PROMO_TYPES = [
    PROMO_TYPE_FREE,
    PROMO_TYPE_2X_FREE,
    PROMO_TYPE_2X_UP,
    PROMO_TYPE_50_OFF,
    PROMO_TYPE_2X_50_OFF,
    PROMO_TYPE_30_OFF,
    PROMO_TYPE_NONE,
]

# 促销类型显示名称
PROMO_TYPE_DISPLAY_NAMES = {
    PROMO_TYPE_FREE: "免费",
    PROMO_TYPE_2X_FREE: "2X免费",
    PROMO_TYPE_2X_UP: "2X上传",
    PROMO_TYPE_50_OFF: "50%下载",
    PROMO_TYPE_2X_50_OFF: "2X上传50%下载",
    PROMO_TYPE_30_OFF: "30%下载",
    PROMO_TYPE_NONE: "无促销",
}

# MTeam API 促销标识映射
MTEAM_PROMO_MAPPING = {
    "FREE": PROMO_TYPE_FREE,
    "2XFREE": PROMO_TYPE_2X_FREE,
    "2X": PROMO_TYPE_2X_UP,
    "HALFDOWN": PROMO_TYPE_50_OFF,
    "2XHALFDOWN": PROMO_TYPE_2X_50_OFF,
    "30%": PROMO_TYPE_30_OFF,
    "NORMAL": PROMO_TYPE_NONE,
}
