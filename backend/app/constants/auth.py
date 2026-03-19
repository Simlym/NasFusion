"""
认证相关常量
"""

# 认证类型
AUTH_TYPE_COOKIE = "cookie"
AUTH_TYPE_PASSKEY = "passkey"
AUTH_TYPE_USER_PASS = "user_pass"

AUTH_TYPES = [
    AUTH_TYPE_COOKIE,
    AUTH_TYPE_PASSKEY,
    AUTH_TYPE_USER_PASS,
]

# 认证类型显示名称
AUTH_TYPE_DISPLAY_NAMES = {
    AUTH_TYPE_COOKIE: "Cookie认证",
    AUTH_TYPE_PASSKEY: "Passkey认证",
    AUTH_TYPE_USER_PASS: "用户名密码认证",
}
