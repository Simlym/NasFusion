# 用户系统表

## 1. users（用户管理）✅ 已实现

**用途**：系统用户基础信息

**实现状态**：✅ 已完整实现（模型文件：`app/models/user.py` - User类）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 用户名 |
| email | VARCHAR(255) | UNIQUE, NULL, INDEX | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'user' | 角色：admin/user |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否激活 |
| is_verified | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否已验证 |
| last_login_at | TIMESTAMP | NULL | 最后登录时间 |
| display_name | VARCHAR(100) | NULL | 显示名称 |
| avatar_url | TEXT | NULL | 头像URL |
| timezone | VARCHAR(50) | NOT NULL, DEFAULT 'UTC' | 时区 |
| language | VARCHAR(10) | NOT NULL, DEFAULT 'zh-CN' | 语言 |
| password_changed_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 密码修改时间 |
| login_attempts | INTEGER | NOT NULL, DEFAULT 0 | 登录尝试次数 |
| locked_until | TIMESTAMP | NULL | 锁定到期时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(username)` - 唯一索引（已在字段定义中实现）
- `UNIQUE(email)` - 唯一索引（已在字段定义中实现）
- `INDEX(username)` - 单独索引（已在字段定义中实现）
- `INDEX(email)` - 单独索引（已在字段定义中实现）

**字段说明**：
- **password_hash**：使用 bcrypt 算法存储密码哈希
- **role**：用户角色，支持 admin（管理员）和 user（普通用户）
- **is_active**：账户是否激活，未激活账户无法登录
- **is_verified**：邮箱是否验证
- **login_attempts**：登录失败次数，用于防暴力破解
- **locked_until**：账户锁定到期时间，超过一定失败次数后自动锁定

---

## 2. user_profiles（用户配置）✅ 已实现

**用途**：用户个人偏好和配置

**实现状态**：✅ 已完整实现（模型文件：`app/models/user.py` - UserProfile类）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, UNIQUE, NOT NULL | 用户ID |
| ui_theme | VARCHAR(20) | NOT NULL, DEFAULT 'auto' | 界面主题：light/dark/auto |
| language | VARCHAR(10) | NOT NULL, DEFAULT 'zh-CN' | 用户界面语言 |
| timezone | VARCHAR(50) | NOT NULL, DEFAULT 'UTC' | 用户时区 |
| items_per_page | INTEGER | NOT NULL, DEFAULT 50 | 每页显示数量 |
| min_seeders | INTEGER | NOT NULL, DEFAULT 1 | 最小做种数要求 |
| max_auto_download_size_gb | INTEGER | NULL | 自动下载最大大小(GB) |
| default_downloader | VARCHAR(50) | NULL | 默认下载器 |
| auto_start_download | BOOLEAN | NOT NULL, DEFAULT TRUE | 自动开始下载 |
| download_path_template | TEXT | NULL | 下载路径模板 |
| notification_enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用通知 |
| email_notifications | BOOLEAN | NOT NULL, DEFAULT FALSE | 邮件通知 |
| push_notifications | BOOLEAN | NOT NULL, DEFAULT TRUE | 推送通知 |
| ai_recommendations_enabled | BOOLEAN | NOT NULL, DEFAULT FALSE | AI推荐开关 |
| recommendation_frequency | VARCHAR(20) | NOT NULL, DEFAULT 'daily' | 推荐频率：daily/weekly |
| share_anonymous_stats | BOOLEAN | NOT NULL, DEFAULT TRUE | 分享匿名统计 |
| public_watchlist | BOOLEAN | NOT NULL, DEFAULT FALSE | 公开观看列表 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(user_id)` - 唯一索引（已在字段定义中实现）

**设计差异说明**：
- **preferred_quality**：原设计中包含此字段，实际实现中暂未添加，将在后续版本中实现
- **max_auto_download_size_gb**：实际实现使用 `Integer` 类型，而非 `DECIMAL(8,2)`

**字段说明**：
- **ui_theme**：界面主题，支持 light（亮色）、dark（暗色）、auto（自动切换）
- **items_per_page**：列表每页显示数量，默认50条
- **min_seeders**：下载时最小做种数要求，低于此值的资源不自动下载
- **max_auto_download_size_gb**：自动下载的最大文件大小限制（GB）
- **download_path_template**：下载路径模板，支持变量替换
- **ai_recommendations_enabled**：是否启用AI推荐功能
- **recommendation_frequency**：AI推荐频率，支持 daily（每日）、weekly（每周）

---

## 3. notification_channels（通知渠道配置）✅ 已实现

**用途**：配置各种通知渠道

**实现状态**：✅ 已完整实现（模型文件：`app/models/notification.py` - NotificationChannel类）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, NULL | 用户ID，NULL表示系统级 |
| channel_type | VARCHAR(30) | NOT NULL | 渠道类型：telegram/email/webhook/discord |
| name | VARCHAR(100) | NOT NULL | 渠道名称 |
| config | JSON | NOT NULL | 渠道特定配置，JSON |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否启用 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'healthy' | 状态：healthy/error |
| last_test_at | TIMESTAMP | NULL | 最后测试时间 |
| last_test_result | TEXT | NULL | 最后测试结果 |
| subscribed_events | JSON | NULL | 订阅的事件类型，JSON数组 |
| priority | INTEGER | NOT NULL, DEFAULT 5 | 渠道优先级(1-10) |
| rate_limit | JSON | NULL | 发送频率限制 |
| supports_html | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否支持HTML格式 |
| supports_markdown | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否支持Markdown格式 |
| max_message_length | INTEGER | NOT NULL, DEFAULT 1000 | 最大消息长度 |
| message_templates | JSON | NULL | 消息模板 |
| failure_handling | JSON | NULL | 失败处理策略 |
| last_success_at | TIMESTAMP | NULL | 最后成功时间 |
| consecutive_failures | INTEGER | NOT NULL, DEFAULT 0 | 连续失败次数 |
| health_check_url | TEXT | NULL | 健康检查URL |
| description | TEXT | NULL | 渠道描述 |
| icon_url | TEXT | NULL | 图标URL |
| color | VARCHAR(7) | NOT NULL, DEFAULT '#007bff' | 渠道颜色 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- 实际实现中未定义额外索引（根据需要可在后续优化中添加）

**字段说明**：
- **user_id**：用户ID，NULL表示系统级通知渠道（所有用户共享）
- **channel_type**：通知渠道类型，支持 telegram、email、webhook、discord 等
- **config**：渠道特定配置，如 Telegram 的 bot_token 和 chat_id
- **enabled**：是否启用该渠道
- **status**：渠道状态，healthy（正常）或 error（异常）
- **subscribed_events**：订阅的事件类型，如下载完成、系统错误等
- **priority**：渠道优先级（1-10），数字越大优先级越高
- **supports_html/supports_markdown**：标识渠道是否支持 HTML 或 Markdown 格式的消息
- **max_message_length**：最大消息长度限制
- **message_templates**：消息模板，可自定义不同事件的通知格式
- **failure_handling**：失败处理策略，如重试次数、重试间隔等
- **consecutive_failures**：连续失败次数，超过阈值可自动禁用渠道
- **color**：渠道颜色（十六进制），用于前端展示
