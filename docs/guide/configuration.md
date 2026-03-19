# 配置说明

所有配置通过 `backend/.env` 文件管理。

## 必填配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | JWT 签名密钥，务必修改 | `openssl rand -hex 32` |
| `DATABASE_URL` | 数据库连接串 | 见下方 |

## 数据库配置

**SQLite（默认，适合个人使用）**

```ini
DATABASE_URL=sqlite+aiosqlite:///./data/nasfusion.db
```

**PostgreSQL（推荐生产环境）**

```ini
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nasfusion
```

## 元数据刮削

```ini
# TMDB（强烈推荐）
TMDB_API_KEY=your_tmdb_api_key
TMDB_LANGUAGE=zh-CN

# 豆瓣（可选）
DOUBAN_ENABLED=true
```

## 代理配置

如果访问 TMDB 或 PT 站点需要代理：

```ini
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

## 通知配置

**Telegram**

```ini
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**邮件**

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
NOTIFICATION_EMAIL=notify@email.com
```

## 时区配置

```ini
TIMEZONE=Asia/Shanghai
```
