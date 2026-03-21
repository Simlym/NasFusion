# 配置说明

NasFusion 的所有配置通过 `backend/.env` 文件管理。本页列出所有可用配置项及其说明。

## 配置文件位置

```
NasFusion/
└── backend/
    ├── .env.example    # 配置模板（带注释，勿直接使用）
    └── .env            # 实际配置（从 .env.example 复制后修改）
```

## 必填配置

这些配置**必须修改**，否则系统无法正常运行或存在安全风险。

```ini
# JWT 签名密钥，用于生成用户 Token
# 生成命令：openssl rand -hex 32
SECRET_KEY=请替换为随机字符串

# TMDB API Key，用于获取电影/剧集元数据
# 申请地址：https://www.themoviedb.org/settings/api
TMDB_API_KEY=你的TMDB_API_Key
```

## 数据库配置

**SQLite（默认，适合个人/小规模使用）**

```ini
DATABASE_URL=sqlite+aiosqlite:///./data/nasfusion.db
```

- 零配置，开箱即用
- 数据文件位于 `backend/data/nasfusion.db`
- 并发写入能力有限，不建议多用户同时大量操作

**PostgreSQL（推荐生产环境）**

```ini
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:5432/nasfusion
```

Docker Compose 中使用内置 PostgreSQL：

```ini
DATABASE_URL=postgresql+asyncpg://nasfusion:nasfusion@db:5432/nasfusion
```

## 元数据配置

```ini
# TMDB（强烈推荐配置）
TMDB_API_KEY=your_tmdb_api_key
TMDB_LANGUAGE=zh-CN          # 返回语言，zh-CN 优先中文
TMDB_BASE_URL=https://api.themoviedb.org/3  # 默认值，一般无需修改

# 豆瓣（可选，作为补充数据源）
DOUBAN_ENABLED=true           # 是否启用豆瓣
DOUBAN_COOKIE=                # 豆瓣 Cookie（某些接口需要）
```

## 代理配置

访问 TMDB 或特定 PT 站点需要代理时配置：

```ini
# 全局代理（HTTP/HTTPS 请求均走此代理）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# SOCKS5 代理示例
HTTP_PROXY=socks5://127.0.0.1:1080
```

::: tip
PT 站点代理可在站点管理页面**单独配置**，无需使用全局代理。
:::

## 下载器配置

```ini
# qBittorrent
QB_HOST=http://127.0.0.1:8080
QB_USERNAME=admin
QB_PASSWORD=adminadmin

# 下载完成后的默认保存路径（容器内路径）
QB_DEFAULT_SAVE_PATH=/downloads
```

## 媒体服务器配置

```ini
# Jellyfin
JELLYFIN_URL=http://192.168.1.100:8096
JELLYFIN_API_KEY=your_jellyfin_api_key

# Emby（与 Jellyfin 配置方式相同）
EMBY_URL=http://192.168.1.100:8096
EMBY_API_KEY=your_emby_api_key

# Plex
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_plex_token
```

## 通知配置

### Telegram

```ini
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFabcdef...
TELEGRAM_CHAT_ID=123456789
```

获取方式：
1. 与 [@BotFather](https://t.me/BotFather) 对话，发送 `/newbot` 创建 Bot
2. 获得 `Bot Token`
3. 与 [@userinfobot](https://t.me/userinfobot) 对话获取你的 `Chat ID`

### 邮件（SMTP）

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password    # Gmail 使用应用专用密码
NOTIFICATION_EMAIL=notify@gmail.com  # 通知发送到此邮箱
```

::: tip Gmail 应用专用密码
Gmail 开启两步验证后，需在 **账户设置 → 安全 → 应用专用密码** 中生成专用密码，不能直接用登录密码。
:::

## 文件整理配置

```ini
# 媒体库根目录（容器内路径）
MEDIA_ROOT=/media

# 整理方式：hardlink（硬链接）| symlink（软链接）| copy（复制）
MEDIA_ORGANIZE_MODE=hardlink

# 电影子目录
MOVIE_DIR=电影

# 电视剧子目录
TV_DIR=电视剧

# 动漫子目录
ANIME_DIR=动漫
```

## 任务调度配置

```ini
# PT 资源同步间隔（小时）
SYNC_INTERVAL_HOURS=6

# 站点健康检查间隔（分钟）
HEALTH_CHECK_INTERVAL_MINUTES=60

# 下载任务监控间隔（分钟）
DOWNLOAD_MONITOR_INTERVAL_MINUTES=5
```

## 系统配置

```ini
# 时区（影响定时任务执行时间）
TIMEZONE=Asia/Shanghai

# 日志级别：DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO

# 最大并发下载任务数
MAX_CONCURRENT_DOWNLOADS=3

# API 访问允许的 CORS 源（多个用逗号分隔）
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 安全配置

```ini
# Token 有效期（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES=10080   # 默认 7 天

# 敏感字段加密密钥（如 API Key 存储加密）
# 与 SECRET_KEY 不同，专用于字段级加密
FIELD_ENCRYPTION_KEY=               # 留空则自动生成
```

## 完整配置模板

以下是一个可直接使用的最小配置示例：

```ini
# ===== 必填 =====
SECRET_KEY=请修改为随机字符串
TMDB_API_KEY=你的TMDB密钥

# ===== 数据库 =====
DATABASE_URL=sqlite+aiosqlite:///./data/nasfusion.db

# ===== 下载器 =====
QB_HOST=http://qbittorrent:8080
QB_USERNAME=admin
QB_PASSWORD=adminadmin

# ===== 媒体服务器 =====
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=你的Jellyfin密钥

# ===== 通知（可选）=====
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ===== 系统 =====
TIMEZONE=Asia/Shanghai
LOG_LEVEL=INFO
```

## 修改配置后重启

Docker 部署时，修改 `.env` 后需重启服务：

```bash
docker compose restart backend
```

或完整重启：

```bash
docker compose down && docker compose up -d
```
