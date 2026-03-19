# NasFusion 通知系统设计文档

## 📖 目录
- [系统概述](#系统概述)
- [核心功能](#核心功能)
- [数据库设计](#数据库设计)
- [通知事件类型](#通知事件类型)
- [通知渠道](#通知渠道)
- [实现架构](#实现架构)
- [前端界面](#前端界面)
- [开发计划](#开发计划)

---

## 系统概述

NasFusion 通知系统分为两大模块:

### 1. 系统内消息通知 (In-App Notifications)
- **用途**: 用户在系统内查看的消息中心
- **特点**: 持久化存储、支持已读/未读、消息分类、优先级
- **场景**: 订阅更新、下载完成、系统警告等

### 2. 对外消息推送 (External Notifications)
- **用途**: 推送到外部渠道（Telegram、Email、Webhook等）
- **特点**: 多渠道支持、规则配置、模板自定义、失败重试
- **场景**: 实时通知用户关注的重要事件

---

## 核心功能

### ✅ 已实现
- **通知渠道配置** (`notification_channels` 表)
  - 支持多种渠道类型
  - 渠道健康检查
  - 优先级管理
  - 频率限制

### 🚧 待实现

#### 1. 系统内消息中心
- **消息列表**: 分页展示、筛选（类型/状态/优先级）
- **未读消息**: 未读数量徽标、一键已读
- **消息详情**: 查看详细信息、相关资源链接
- **消息管理**: 删除、清空、自动过期

#### 2. 通知规则配置
- **事件订阅**: 选择哪些事件触发通知
- **渠道选择**: 不同事件使用不同渠道
- **过滤条件**: 自定义触发条件（如文件大小、质量等）
- **静默时段**: 设置免打扰时间段
- **去重策略**: 避免重复通知

#### 3. 通知模板系统
- **预设模板**: 为每种事件类型提供默认模板
- **自定义模板**: 支持变量替换（如 `{title}`, `{size}`, `{quality}`）
- **多语言支持**: 根据用户语言选择模板
- **格式支持**: Markdown、HTML、纯文本

#### 4. 通知发送日志
- **发送历史**: 记录所有通知发送情况
- **失败重试**: 自动重试失败的通知
- **统计分析**: 发送成功率、渠道健康度
- **调试工具**: 查看发送失败原因

---

## 数据库设计

### 1. system_notifications（系统内消息）🆕

**用途**: 存储系统内消息中心的通知消息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, NULL | 用户ID，NULL表示系统广播 |
| notification_type | VARCHAR(50) | NOT NULL | 通知类型（见通知事件类型） |
| title | VARCHAR(200) | NOT NULL | 通知标题 |
| content | TEXT | NOT NULL | 通知内容 |
| priority | VARCHAR(20) | NOT NULL, DEFAULT 'normal' | 优先级：low/normal/high/urgent |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'unread' | 状态：unread/read/archived |
| related_type | VARCHAR(50) | NULL | 关联资源类型：pt_resource/subscription/download_task |
| related_id | INTEGER | NULL | 关联资源ID |
| metadata | JSON | NULL | 扩展数据（JSON） |
| read_at | TIMESTAMP | NULL | 阅读时间 |
| expires_at | TIMESTAMP | NULL | 过期时间（过期后自动清理） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
```sql
CREATE INDEX idx_system_notifications_user_status ON system_notifications(user_id, status);
CREATE INDEX idx_system_notifications_type ON system_notifications(notification_type);
CREATE INDEX idx_system_notifications_created_at ON system_notifications(created_at DESC);
CREATE INDEX idx_system_notifications_expires_at ON system_notifications(expires_at) WHERE expires_at IS NOT NULL;
```

---

### 2. notification_rules（通知规则）🆕

**用途**: 配置哪些事件触发哪些渠道的通知

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, NOT NULL | 用户ID |
| name | VARCHAR(100) | NOT NULL | 规则名称 |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否启用 |
| event_type | VARCHAR(50) | NOT NULL | 事件类型（见通知事件类型） |
| conditions | JSON | NULL | 触发条件（JSON） |
| channel_ids | JSON | NOT NULL | 通知渠道ID列表（JSON数组） |
| send_in_app | BOOLEAN | NOT NULL, DEFAULT TRUE | 发送系统内通知 |
| template_id | INTEGER | FK → notification_templates, NULL | 使用的模板ID |
| silent_hours | JSON | NULL | 静默时段配置（JSON） |
| deduplication_window | INTEGER | NULL | 去重时间窗口（秒） |
| priority | INTEGER | NOT NULL, DEFAULT 5 | 规则优先级（1-10） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
```sql
CREATE INDEX idx_notification_rules_user_enabled ON notification_rules(user_id, enabled);
CREATE INDEX idx_notification_rules_event_type ON notification_rules(event_type);
```

**条件示例** (`conditions` 字段):
```json
{
  "min_size_gb": 10,
  "quality": ["1080p", "2160p"],
  "promotion_types": ["free", "2x_free"],
  "sites": ["mteam", "hdchina"]
}
```

**静默时段示例** (`silent_hours` 字段):
```json
{
  "enabled": true,
  "periods": [
    {"start": "22:00", "end": "08:00", "days": ["mon", "tue", "wed", "thu", "fri"]},
    {"start": "23:00", "end": "09:00", "days": ["sat", "sun"]}
  ]
}
```

---

### 3. notification_templates（通知模板）🆕

**用途**: 存储可重用的通知消息模板

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, NULL | 用户ID，NULL表示系统模板 |
| event_type | VARCHAR(50) | NOT NULL | 事件类型 |
| name | VARCHAR(100) | NOT NULL | 模板名称 |
| language | VARCHAR(10) | NOT NULL, DEFAULT 'zh-CN' | 语言 |
| format | VARCHAR(20) | NOT NULL, DEFAULT 'markdown' | 格式：markdown/html/text |
| title_template | VARCHAR(200) | NOT NULL | 标题模板 |
| content_template | TEXT | NOT NULL | 内容模板 |
| variables | JSON | NULL | 可用变量说明（JSON） |
| is_system | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否系统模板 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
```sql
CREATE UNIQUE INDEX idx_notification_templates_unique ON notification_templates(user_id, event_type, language) WHERE user_id IS NOT NULL;
CREATE INDEX idx_notification_templates_event_type ON notification_templates(event_type);
```

**模板示例**:
```markdown
# 标题模板
[{site_name}] 订阅匹配: {title}

# 内容模板
🎬 **{title}** ({year})

📦 **大小**: {size}
🎯 **质量**: {quality}
⚡ **促销**: {promotion}
👥 **做种**: {seeders}

🔗 [查看详情]({resource_url})
```

---

### 4. notification_logs（通知发送日志）🆕

**用途**: 记录所有通知发送历史

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, NULL | 用户ID |
| notification_type | VARCHAR(50) | NOT NULL | 通知类型 |
| channel_id | INTEGER | FK → notification_channels, NULL | 通知渠道ID（系统内通知为NULL） |
| channel_type | VARCHAR(30) | NULL | 渠道类型 |
| title | VARCHAR(200) | NOT NULL | 通知标题 |
| content | TEXT | NOT NULL | 通知内容 |
| status | VARCHAR(20) | NOT NULL | 状态：pending/sent/failed |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 | 重试次数 |
| error_message | TEXT | NULL | 错误信息 |
| sent_at | TIMESTAMP | NULL | 发送时间 |
| response_data | JSON | NULL | 渠道返回数据（JSON） |
| metadata | JSON | NULL | 扩展数据（JSON） |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
```sql
CREATE INDEX idx_notification_logs_user_created ON notification_logs(user_id, created_at DESC);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);
CREATE INDEX idx_notification_logs_channel ON notification_logs(channel_id);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);
```

---

## 通知事件类型

基于现有功能,定义以下通知事件类型（常量定义在 `app/constants/notification.py`）:

### 1. 订阅相关 (Subscription)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `subscription_matched` | 订阅匹配到新资源 | ✅ | ✅ |
| `subscription_downloaded` | 订阅资源已下载 | ✅ | ✅ |
| `subscription_completed` | 订阅季度完成 | ✅ | ✅ |
| `subscription_no_resource` | 订阅长期无资源提醒 | ✅ | 🔕 |

### 2. 下载相关 (Download)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `download_started` | 下载开始 | ✅ | 🔕 |
| `download_completed` | 下载完成 | ✅ | ✅ |
| `download_failed` | 下载失败 | ✅ | ✅ |
| `download_paused` | 下载暂停 | ✅ | 🔕 |

### 3. 资源相关 (Resource)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `resource_free_promotion` | 发现免费资源 | ✅ | ✅ |
| `resource_2x_promotion` | 发现2x促销资源 | ✅ | 🔕 |
| `resource_high_quality` | 发现高质量资源 | ✅ | 🔕 |

### 4. PT站点相关 (PT Site)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `site_connection_failed` | 站点连接失败 | ✅ | ✅ |
| `site_auth_expired` | 站点认证过期 | ✅ | ✅ |
| `site_sync_completed` | 站点同步完成 | ✅ | 🔕 |

### 5. 媒体文件相关 (Media)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `media_scan_completed` | 媒体扫描完成 | ✅ | 🔕 |
| `media_organized` | 文件整理完成 | ✅ | ✅ |
| `media_metadata_scraped` | 元数据刮削完成 | ✅ | 🔕 |

### 6. 任务相关 (Task)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `task_failed` | 定时任务执行失败 | ✅ | ✅ |
| `task_completed` | 批量任务完成 | ✅ | 🔕 |

### 7. 系统相关 (System)
| 事件类型 | 说明 | 系统内 | 对外推送 |
|---------|------|--------|---------|
| `system_error` | 系统错误警告 | ✅ | ✅ |
| `disk_space_low` | 磁盘空间不足 | ✅ | ✅ |
| `user_login_anomaly` | 用户登录异常 | ✅ | ✅ |
| `system_update_available` | 系统更新可用 | ✅ | 🔕 |

> **图例**: ✅ 默认启用 | 🔕 默认关闭（用户可配置）

---

## 通知渠道

### 已支持渠道（基于 `notification_channels` 表）

#### 1. Telegram Bot
**配置字段** (`config` JSON):
```json
{
  "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "chat_id": "123456789",
  "parse_mode": "Markdown",
  "disable_notification": false
}
```

**特性**:
- ✅ 支持 Markdown 格式
- ✅ 支持 HTML 格式
- ✅ 支持静音推送
- ✅ 最大消息长度: 4096字符

---

#### 2. Email (SMTP)
**配置字段** (`config` JSON):
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "your-email@gmail.com",
  "smtp_password": "your-app-password",
  "from_name": "NasFusion",
  "from_email": "noreply@nasfusion.com",
  "to_email": "user@example.com",
  "use_tls": true
}
```

**特性**:
- ✅ 支持 HTML 格式
- ✅ 支持附件
- ✅ 支持 CC/BCC
- ✅ 最大消息长度: 无限制

---

#### 3. Webhook
**配置字段** (`config` JSON):
```json
{
  "url": "https://your-webhook.com/api/notifications",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer your-token",
    "Content-Type": "application/json"
  },
  "body_template": {
    "title": "{title}",
    "content": "{content}",
    "timestamp": "{timestamp}"
  }
}
```

**特性**:
- ✅ 自定义请求方法（POST/PUT）
- ✅ 自定义请求头
- ✅ 自定义请求体模板
- ✅ 支持变量替换

---

### 🚧 规划支持的渠道

#### 4. 企业微信 (WeCom)
```json
{
  "corp_id": "ww123456",
  "corp_secret": "secret",
  "agent_id": "1000002",
  "to_user": "@all"
}
```

#### 5. 钉钉 (DingTalk)
```json
{
  "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "secret": "SECxxxx",
  "at_mobiles": ["13800138000"],
  "is_at_all": false
}
```

#### 6. Bark (iOS)
```json
{
  "device_key": "your-device-key",
  "server_url": "https://api.day.app",
  "sound": "birdsong",
  "icon": "https://your-icon.png"
}
```

#### 7. Discord
```json
{
  "webhook_url": "https://discord.com/api/webhooks/xxx/yyy",
  "username": "NasFusion",
  "avatar_url": "https://your-avatar.png"
}
```

#### 8. Gotify
```json
{
  "server_url": "https://gotify.example.com",
  "app_token": "your-app-token",
  "priority": 5
}
```

#### 9. PushPlus
```json
{
  "token": "your-pushplus-token",
  "topic": "nasfusion",
  "template": "html"
}
```

---

## 实现架构

### 1. Service 层设计

```
NotificationService
├── send_notification()           # 发送通知（统一入口）
├── send_in_app_notification()    # 发送系统内通知
├── send_external_notification()  # 发送外部通知
├── create_notification()         # 创建通知记录
├── mark_as_read()                # 标记已读
├── get_unread_count()            # 获取未读数量
├── get_user_notifications()      # 获取用户通知列表
└── cleanup_expired()             # 清理过期通知

NotificationRuleService
├── get_rules_for_event()         # 获取事件对应的规则
├── check_conditions()            # 检查触发条件
├── is_in_silent_hours()          # 检查是否在静默时段
└── should_deduplicate()          # 检查是否应去重

NotificationChannelService
├── test_channel()                # 测试渠道连接
├── send_via_channel()            # 通过渠道发送
├── update_channel_health()       # 更新渠道健康状态
└── get_enabled_channels()        # 获取启用的渠道

NotificationTemplateService
├── render_template()             # 渲染模板
├── get_template_for_event()      # 获取事件模板
└── validate_template()           # 验证模板语法

NotificationLogService
├── log_notification()            # 记录通知日志
├── update_send_status()          # 更新发送状态
├── retry_failed()                # 重试失败通知
└── get_statistics()              # 获取统计数据
```

---

### 2. Adapter 层设计（通知渠道适配器）

```
app/adapters/notification_channels/
├── __init__.py
├── base.py                       # BaseNotificationChannel（抽象基类）
├── telegram.py                   # TelegramNotificationChannel
├── email.py                      # EmailNotificationChannel
├── webhook.py                    # WebhookNotificationChannel
├── wecom.py                      # WeComNotificationChannel（企业微信）
├── dingtalk.py                   # DingTalkNotificationChannel
├── bark.py                       # BarkNotificationChannel
├── discord.py                    # DiscordNotificationChannel
├── gotify.py                     # GotifyNotificationChannel
└── pushplus.py                   # PushPlusNotificationChannel
```

**基类设计** (`base.py`):
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseNotificationChannel(ABC):
    """通知渠道基类"""

    @abstractmethod
    async def send(self, title: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        发送通知

        Args:
            title: 通知标题
            content: 通知内容
            **kwargs: 额外参数

        Returns:
            {"success": bool, "message": str, "data": dict}
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        Returns:
            {"success": bool, "message": str}
        """
        pass

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """渠道类型标识"""
        pass

    @property
    def supports_markdown(self) -> bool:
        """是否支持 Markdown"""
        return False

    @property
    def supports_html(self) -> bool:
        """是否支持 HTML"""
        return False

    @property
    def max_message_length(self) -> int:
        """最大消息长度"""
        return 1000
```

---

### 3. 通知发送流程

```
触发事件（如订阅匹配）
    ↓
NotificationService.send_notification(event_type, data, user_id)
    ↓
获取用户通知规则 (NotificationRuleService.get_rules_for_event)
    ↓
检查触发条件 (check_conditions) ──→ 不满足 ──→ 结束
    ↓ 满足
检查静默时段 (is_in_silent_hours) ──→ 在静默时段 ──→ 结束
    ↓ 不在
检查去重 (should_deduplicate) ──→ 重复 ──→ 结束
    ↓ 不重复
渲染消息模板 (NotificationTemplateService.render_template)
    ↓
并行执行:
├── 发送系统内通知 (send_in_app_notification)
│   ├── 创建 system_notifications 记录
│   └── 返回
└── 发送外部通知 (send_external_notification)
    ├── 遍历规则中的渠道列表
    ├── 通过适配器发送 (adapter.send)
    ├── 记录发送日志 (NotificationLogService.log_notification)
    └── 更新渠道健康状态 (update_channel_health)
```

---

### 4. 与现有系统集成点

在业务逻辑中插入通知触发点:

```python
# 示例: 订阅匹配时发送通知
# app/services/subscription_service.py

async def check_subscription(db: AsyncSession, subscription_id: int):
    # ... 订阅检查逻辑 ...

    if matched_resources:
        # 发送通知
        await NotificationService.send_notification(
            db=db,
            event_type=NOTIFICATION_EVENT_SUBSCRIPTION_MATCHED,
            user_id=subscription.user_id,
            data={
                "subscription_id": subscription.id,
                "subscription_name": subscription.name,
                "resource_id": matched_resource.id,
                "title": matched_resource.title,
                "size": matched_resource.size,
                "quality": matched_resource.quality,
                "promotion": matched_resource.promotion_type,
                "site_name": matched_resource.site.name
            },
            related_type="subscription",
            related_id=subscription.id
        )
```

---

## 前端界面

### 1. 消息中心（系统内通知）

**路由**: `/notifications`

**布局设计**:
```
┌─────────────────────────────────────────────────────┐
│  消息中心                              [全部已读] [设置]  │
├─────────────────────────────────────────────────────┤
│  筛选: [全部▼] [未读▼] [类型▼] [优先级▼]              │
├─────────────────────────────────────────────────────┤
│  🔴 [订阅] 订阅匹配: 进击的巨人 最终季 Part 3            │
│     MTeam | 1080p | 免费 | 2小时前                    │
├─────────────────────────────────────────────────────┤
│  ⚪ [下载] 下载完成: 进击的巨人 S04E28                  │
│     qBittorrent | 2.3GB | 5小时前                    │
├─────────────────────────────────────────────────────┤
│  🔴 [系统] 磁盘空间不足警告                            │
│     剩余: 15GB / 500GB (3%) | 1天前                  │
└─────────────────────────────────────────────────────┘
```

**功能**:
- ✅ 未读消息徽标（导航栏）
- ✅ 消息分类筛选
- ✅ 优先级标识（红/黄/绿）
- ✅ 点击查看详情
- ✅ 关联资源快速跳转
- ✅ 批量操作（全部已读、删除）

---

### 2. 通知设置页面

**路由**: `/settings/notifications`

**Tab 设计**:

#### Tab 1: 通知规则
```
┌─────────────────────────────────────────────────────┐
│  通知规则                                  [+ 新建规则]  │
├─────────────────────────────────────────────────────┤
│  ✅ 订阅匹配通知                              [编辑]   │
│     事件: 订阅匹配 | 渠道: Telegram, 系统内            │
│     条件: 所有资源                                    │
├─────────────────────────────────────────────────────┤
│  ✅ 下载完成通知                              [编辑]   │
│     事件: 下载完成 | 渠道: 系统内                      │
│     条件: 大小 > 5GB                                 │
├─────────────────────────────────────────────────────┤
│  ❌ 免费资源提醒                              [编辑]   │
│     事件: 免费促销 | 渠道: Telegram                   │
│     条件: 高质量 (1080p+)                            │
└─────────────────────────────────────────────────────┘
```

**规则编辑弹窗**:
```
┌─────────────────────────────────────┐
│  编辑通知规则                          │
├─────────────────────────────────────┤
│  规则名称: [订阅匹配通知            ]  │
│  事件类型: [订阅匹配         ▼]       │
│  □ 启用此规则                         │
│                                      │
│  通知渠道:                            │
│  ☑ 系统内消息                         │
│  ☑ Telegram Bot                      │
│  ☐ Email                             │
│                                      │
│  触发条件:                            │
│  最小大小: [___] GB                   │
│  质量要求: ☐ 720p ☑ 1080p ☑ 2160p   │
│  促销类型: ☑ 免费 ☑ 2x ☐ 50%        │
│  站点限制: [全部         ▼]          │
│                                      │
│  静默时段:                            │
│  ☑ 启用免打扰                         │
│  时间: [22:00] - [08:00]             │
│  工作日: ☑ 周一-周五                  │
│                                      │
│  去重设置:                            │
│  去重窗口: [300] 秒                   │
│                                      │
│  [取消]              [保存]          │
└─────────────────────────────────────┘
```

---

#### Tab 2: 通知渠道
```
┌─────────────────────────────────────────────────────┐
│  通知渠道                                 [+ 添加渠道]  │
├─────────────────────────────────────────────────────┤
│  ✅ Telegram Bot                          [测试][编辑]│
│     状态: 🟢 正常 | 最后发送: 2小时前                  │
│     订阅事件: 订阅匹配、下载完成、系统错误              │
├─────────────────────────────────────────────────────┤
│  ❌ Email (SMTP)                          [测试][编辑]│
│     状态: 🔴 连接失败 | 最后测试: 1天前                │
│     错误: SMTP authentication failed                │
├─────────────────────────────────────────────────────┤
│  ✅ Webhook                               [测试][编辑]│
│     状态: 🟢 正常 | 最后发送: 5分钟前                  │
│     URL: https://your-webhook.com/api/notify        │
└─────────────────────────────────────────────────────┘
```

**渠道配置表单** (以 Telegram 为例):
```
┌─────────────────────────────────────┐
│  配置 Telegram 通知                   │
├─────────────────────────────────────┤
│  渠道名称: [Telegram Bot         ]   │
│  Bot Token: [123456:ABC-DEF...   ]   │
│  Chat ID: [123456789             ]   │
│                                      │
│  消息格式: [Markdown        ▼]       │
│  □ 静音推送                           │
│                                      │
│  订阅事件:                            │
│  ☑ 订阅匹配                           │
│  ☑ 下载完成                           │
│  ☑ 下载失败                           │
│  ☑ 站点连接失败                        │
│  ☑ 系统错误                           │
│  ☐ 媒体扫描完成                        │
│                                      │
│  频率限制:                            │
│  每分钟最多: [10] 条                  │
│  每小时最多: [100] 条                 │
│                                      │
│  [取消]       [测试连接]    [保存]    │
└─────────────────────────────────────┘
```

---

#### Tab 3: 消息模板
```
┌─────────────────────────────────────────────────────┐
│  消息模板                                 [+ 新建模板]  │
├─────────────────────────────────────────────────────┤
│  订阅匹配通知模板                            [编辑]   │
│     语言: 中文 | 格式: Markdown                       │
│     预览: [{site_name}] 订阅匹配: {title}             │
├─────────────────────────────────────────────────────┤
│  下载完成通知模板                            [编辑]   │
│     语言: 中文 | 格式: Markdown                       │
│     预览: ✅ 下载完成: {title}                        │
└─────────────────────────────────────────────────────┘
```

**模板编辑器**:
```
┌─────────────────────────────────────┐
│  编辑模板: 订阅匹配通知                │
├─────────────────────────────────────┤
│  事件类型: [订阅匹配         ▼]       │
│  语言: [中文 (zh-CN)    ▼]           │
│  格式: [Markdown        ▼]           │
│                                      │
│  标题模板:                            │
│  ┌─────────────────────────────┐   │
│  │ [{site_name}] 订阅匹配: {title}│  │
│  └─────────────────────────────┘   │
│                                      │
│  内容模板:                            │
│  ┌─────────────────────────────┐   │
│  │ 🎬 **{title}** ({year})      │   │
│  │                              │   │
│  │ 📦 **大小**: {size}          │   │
│  │ 🎯 **质量**: {quality}       │   │
│  │ ⚡ **促销**: {promotion}     │   │
│  │ 👥 **做种**: {seeders}       │   │
│  │                              │   │
│  │ 🔗 [查看详情]({resource_url})│   │
│  └─────────────────────────────┘   │
│                                      │
│  可用变量:                            │
│  {title}, {site_name}, {size},       │
│  {quality}, {promotion}, {seeders},  │
│  {year}, {resource_url}              │
│                                      │
│  预览:                                │
│  ┌─────────────────────────────┐   │
│  │ [MTeam] 订阅匹配: 进击的巨人   │   │
│  │                              │   │
│  │ 🎬 **进击的巨人 最终季** (2023)│  │
│  │ 📦 **大小**: 2.3GB           │   │
│  │ 🎯 **质量**: 1080p           │   │
│  │ ⚡ **促销**: 免费             │   │
│  │ 👥 **做种**: 125             │   │
│  └─────────────────────────────┘   │
│                                      │
│  [取消]              [保存]          │
└─────────────────────────────────────┘
```

---

#### Tab 4: 通知日志
```
┌─────────────────────────────────────────────────────┐
│  通知日志                          [刷新] [清空日志]   │
├─────────────────────────────────────────────────────┤
│  筛选: [全部状态▼] [全部渠道▼] [最近7天▼]             │
├─────────────────────────────────────────────────────┤
│  ✅ [Telegram] 订阅匹配: 进击的巨人                   │
│     发送时间: 2小时前 | 耗时: 0.5s                    │
├─────────────────────────────────────────────────────┤
│  ✅ [系统内] 下载完成: xxx                            │
│     发送时间: 5小时前                                 │
├─────────────────────────────────────────────────────┤
│  ❌ [Email] 系统错误警告                              │
│     发送时间: 1天前 | 重试: 3次                       │
│     错误: SMTP connection timeout                   │
│     [重新发送]                                        │
└─────────────────────────────────────────────────────┘
```

---

### 3. 消息通知 API

```typescript
// frontend/src/api/notifications.ts

// 系统内消息
export function getNotifications(params: NotificationQuery) {
  return request.get<NotificationListResponse>('/notifications', { params })
}

export function getUnreadCount() {
  return request.get<{ count: number }>('/notifications/unread-count')
}

export function markAsRead(id: number) {
  return request.put(`/notifications/${id}/read`)
}

export function markAllAsRead() {
  return request.put('/notifications/read-all')
}

// 通知规则
export function getNotificationRules() {
  return request.get<NotificationRuleListResponse>('/notification-rules')
}

export function createNotificationRule(data: NotificationRuleCreate) {
  return request.post('/notification-rules', data)
}

// 通知渠道
export function getNotificationChannels() {
  return request.get<NotificationChannelListResponse>('/notification-channels')
}

export function testNotificationChannel(id: number) {
  return request.post(`/notification-channels/${id}/test`)
}

// 通知日志
export function getNotificationLogs(params: NotificationLogQuery) {
  return request.get<NotificationLogListResponse>('/notification-logs', { params })
}
```

---

## 开发计划

### Phase 1: 基础设施（1-2周）

**目标**: 建立通知系统基础框架

#### 1.1 数据库设计 ✅
- [x] 创建 `system_notifications` 表
- [x] 创建 `notification_rules` 表
- [x] 创建 `notification_templates` 表
- [x] 创建 `notification_logs` 表
- [x] 编写迁移脚本

#### 1.2 常量定义
- [ ] 创建 `app/constants/notification.py`
- [ ] 定义通知事件类型常量
- [ ] 定义通知优先级常量
- [ ] 定义通知状态常量
- [ ] 定义渠道类型常量

#### 1.3 模型定义
- [ ] 创建 `SystemNotification` 模型
- [ ] 创建 `NotificationRule` 模型
- [ ] 创建 `NotificationTemplate` 模型
- [ ] 创建 `NotificationLog` 模型

#### 1.4 Schema 定义
- [ ] 创建 Pydantic schemas
- [ ] 定义请求/响应模型

---

### Phase 2: 系统内通知（1周）

**目标**: 实现消息中心基础功能

#### 2.1 后端开发
- [ ] 实现 `NotificationService`
  - [ ] `send_in_app_notification()`
  - [ ] `get_user_notifications()`
  - [ ] `mark_as_read()`
  - [ ] `get_unread_count()`
  - [ ] `cleanup_expired()`
- [ ] 创建 API 路由 (`api/v1/notifications.py`)
- [ ] 编写单元测试

#### 2.2 前端开发
- [ ] 创建消息中心页面 (`views/Notifications.vue`)
- [ ] 导航栏未读消息徽标组件
- [ ] 消息列表组件
- [ ] 消息详情弹窗
- [ ] API 集成 (`api/notifications.ts`)

---

### Phase 3: 通知渠道适配器（2周）

**目标**: 实现主要通知渠道

#### 3.1 基础设施
- [ ] 创建 `app/adapters/notification_channels/`
- [ ] 实现 `BaseNotificationChannel` 抽象类
- [ ] 创建渠道工厂模式

#### 3.2 渠道实现（优先级排序）
1. [ ] **Telegram Bot** (最常用)
   - [ ] 实现 `TelegramNotificationChannel`
   - [ ] 支持 Markdown 格式
   - [ ] 测试连接功能

2. [ ] **Email (SMTP)**
   - [ ] 实现 `EmailNotificationChannel`
   - [ ] 支持 HTML 格式
   - [ ] SMTP 配置测试

3. [ ] **Webhook**
   - [ ] 实现 `WebhookNotificationChannel`
   - [ ] 自定义请求模板
   - [ ] 重试机制

4. [ ] **Bark (iOS)**
   - [ ] 实现 `BarkNotificationChannel`
   - [ ] 支持自定义图标/声音

5. [ ] **企业微信**
   - [ ] 实现 `WeComNotificationChannel`

#### 3.3 Service 开发
- [ ] 实现 `NotificationChannelService`
  - [ ] `send_via_channel()`
  - [ ] `test_channel()`
  - [ ] `update_channel_health()`
- [ ] 实现失败重试机制
- [ ] 实现频率限制

---

### Phase 4: 通知规则系统（1-2周）

**目标**: 实现智能通知规则配置

#### 4.1 后端开发
- [ ] 实现 `NotificationRuleService`
  - [ ] `get_rules_for_event()`
  - [ ] `check_conditions()`
  - [ ] `is_in_silent_hours()`
  - [ ] `should_deduplicate()`
- [ ] 实现 `NotificationTemplateService`
  - [ ] `render_template()`
  - [ ] `get_template_for_event()`
  - [ ] 模板变量替换引擎
- [ ] 创建 API 路由
  - [ ] `/notification-rules`
  - [ ] `/notification-templates`

#### 4.2 前端开发
- [ ] 通知规则管理页面
- [ ] 规则编辑弹窗（条件配置）
- [ ] 静默时段配置组件
- [ ] 通知模板编辑器
- [ ] 模板预览功能

---

### Phase 5: 集成与测试（1周）

**目标**: 与现有系统集成并测试

#### 5.1 业务集成
- [ ] 订阅系统集成
  - [ ] 订阅匹配通知
  - [ ] 订阅完成通知
- [ ] 下载系统集成
  - [ ] 下载开始通知
  - [ ] 下载完成通知
  - [ ] 下载失败通知
- [ ] PT站点集成
  - [ ] 站点连接失败通知
  - [ ] 站点认证过期通知
- [ ] 媒体文件集成
  - [ ] 文件扫描完成通知
  - [ ] 文件整理完成通知
- [ ] 系统监控集成
  - [ ] 磁盘空间不足通知
  - [ ] 系统错误通知

#### 5.2 测试
- [ ] 单元测试
- [ ] 集成测试
- [ ] 端到端测试
- [ ] 性能测试（大量通知场景）

#### 5.3 文档
- [ ] 更新 `CLAUDE.md`
- [ ] 用户使用手册
- [ ] API 文档完善

---

### Phase 6: 优化与扩展（持续）

**目标**: 性能优化和功能扩展

#### 6.1 性能优化
- [ ] 通知批量发送
- [ ] 异步队列优化
- [ ] 数据库查询优化
- [ ] 缓存策略

#### 6.2 功能扩展
- [ ] 通知统计分析
- [ ] 通知历史趋势图
- [ ] 移动端推送（PWA）
- [ ] WebSocket 实时推送
- [ ] 通知分组/标签
- [ ] 通知优先级排序

---

## 附录

### A. 数据库 ER 图

```
users
  ↓ (1:N)
notification_channels ──┐
  ↓ (N:M via notification_rules.channel_ids)
notification_rules
  ↓ (1:N)
notification_logs

users
  ↓ (1:N)
system_notifications

notification_rules
  ↓ (N:1)
notification_templates
```

---

### B. 通知优先级定义

| 级别 | 标识 | 说明 | UI 颜色 | 示例 |
|------|------|------|---------|------|
| 低 | `low` | 信息性通知 | 🟢 绿色 | 媒体扫描完成 |
| 普通 | `normal` | 日常通知 | 🔵 蓝色 | 订阅匹配 |
| 高 | `high` | 重要通知 | 🟡 黄色 | 下载失败 |
| 紧急 | `urgent` | 紧急通知 | 🔴 红色 | 磁盘空间不足 |

---

### C. 消息模板变量参考

#### 通用变量
- `{timestamp}` - 时间戳
- `{user_name}` - 用户名
- `{site_name}` - PT站点名称

#### 资源相关
- `{title}` - 资源标题
- `{year}` - 年份
- `{size}` - 文件大小
- `{quality}` - 质量
- `{promotion}` - 促销类型
- `{seeders}` - 做种数
- `{leechers}` - 下载数
- `{resource_url}` - 资源链接

#### 订阅相关
- `{subscription_name}` - 订阅名称
- `{season}` - 季度
- `{episode}` - 集数

#### 下载相关
- `{download_path}` - 下载路径
- `{progress}` - 下载进度
- `{speed}` - 下载速度
- `{eta}` - 预计完成时间

#### 系统相关
- `{error_message}` - 错误信息
- `{disk_free}` - 剩余磁盘空间
- `{disk_total}` - 总磁盘空间

---

## 总结

本设计文档为 NasFusion 通知系统提供了完整的技术方案,涵盖:

✅ **系统内消息通知**: 用户消息中心,支持未读管理、分类筛选
✅ **对外消息推送**: 多渠道支持（Telegram、Email、Webhook等）
✅ **通知规则配置**: 灵活的事件订阅、条件过滤、静默时段
✅ **通知模板系统**: 自定义消息格式,支持变量替换
✅ **通知日志追踪**: 完整的发送历史、失败重试、统计分析

**预计开发周期**: 6-8周（分阶段实施）
**技术栈**: FastAPI + SQLAlchemy + Vue3 + TypeScript
**核心优势**:
- 架构清晰,易于扩展新渠道
- 规则灵活,满足不同用户需求
- 完善的日志,便于问题排查

---

**文档版本**: v1.0
**创建日期**: 2025-11-28
**维护者**: Claude Code
**关联文档**: [CLAUDE.md](../../CLAUDE.md) | [数据库设计](./database/README.md)
