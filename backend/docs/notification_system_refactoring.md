# 通知系统架构重构总结文档

> **重构日期**：2025-11-30
>
> **目标**：解决通知系统 Service 层职责不清、命名混淆的问题

---

## 📊 重构概述

### 核心问题
1. **命名混淆**：`notification_service.py` 暗示管理全部通知，实际只管站内消息
2. **职责分散**：站外消息 CRUD 分散在 dispatch_service（创建）和 API 层（查询）
3. **方法归属错误**：`get_dispatch_statistics()` 是查询统计功能，却放在"调度服务"中
4. **跳过 Service 层**：API 直接写 SQL 查询站外消息

### 解决方案
创建清晰的三层 Service 架构：
- `NotificationInternalService` - 站内消息管理
- `NotificationExternalService` - 站外消息管理
- `NotificationDispatchService` - 事件调度分发

---

## 🏗️ 架构对比

### 重构前

```
backend/app/services/
├── notification_service.py              # 站内消息（命名混淆）
├── notification_dispatch_service.py     # 调度 + 站外日志 + 统计（职责过多）
├── notification_channel_service.py      # 渠道管理
├── notification_rule_service.py         # 规则管理
└── notification_template_service.py     # 模板管理
```

**问题**：
- ❌ `notification_service.py` 命名暗示管理全部，实际只管站内
- ❌ 站外消息的创建在 `dispatch_service.py`（Line 295-360）
- ❌ 站外消息的查询在 API 层（直接 SQL）
- ❌ 站外消息统计在 `dispatch_service.py`（Line 499-608）

### 重构后

```
backend/app/services/
├── notification_internal_service.py     # 站内消息 CRUD + 统计
├── notification_external_service.py     # 站外消息 CRUD + 统计 (新增)
├── notification_dispatch_service.py     # 事件调度 + 消息分发（职责收窄）
├── notification_channel_service.py      # 渠道管理
├── notification_rule_service.py         # 规则管理
├── notification_template_service.py     # 模板管理
└── notification_service.py              # 兼容性别名
```

**优势**：
- ✅ 命名清晰：Internal vs External 明确区分
- ✅ 职责单一：每个 Service 只管一类数据
- ✅ 符合分层：API → Service → Database
- ✅ 易于维护：站外消息功能集中管理
- ✅ 向后兼容：通过别名保持旧代码可用

---

## 📝 详细变更

### 1. 新增文件

#### `notification_external_service.py`（298 行）

**功能**：
```python
class NotificationExternalService:
    @staticmethod
    async def create_log(db, log_data) -> NotificationExternal
        """记录站外消息发送日志"""

    @staticmethod
    async def get_by_id(db, log_id) -> Optional[NotificationExternal]
        """获取单条日志详情"""

    @staticmethod
    async def get_user_logs(db, user_id, skip, limit, ...) -> Tuple[List, int]
        """分页查询用户的站外消息历史"""

    @staticmethod
    async def get_statistics(db, user_id, days=7) -> Dict[str, Any]
        """站外消息统计（从 dispatch_service 迁移）"""

    @staticmethod
    async def update_status(db, log_id, status, ...) -> Optional[NotificationExternal]
        """更新发送状态（预留重试机制）"""
```

**数据表**：`notification_external`

**迁移来源**：
- `create_log()` ← `dispatch_service.py` Line 295-360（日志创建逻辑）
- `get_statistics()` ← `dispatch_service.py` Line 499-608（统计方法）
- `get_user_logs()` ← `notifications.py` API Line 326-364（SQL 查询）

---

### 2. 重命名文件

#### `notification_service.py` → `notification_internal_service.py`

**类名变更**：
- `NotificationService` → `NotificationInternalService`

**文档更新**：
```python
# -*- coding: utf-8 -*-
"""
站内通知服务层

负责管理用户在系统内收到的通知（站内信）
包括：通知创建、查询、标记已读、删除等
"""
```

**功能保持不变**：
- `create_notification()` - 创建站内通知
- `send_in_app_notification()` - 快捷发送
- `get_user_notifications()` - 查询列表
- `mark_as_read()` - 标记已读
- `cleanup_expired()` - 清理过期
- ... 其他方法

---

### 3. 修改文件

#### `notification_dispatch_service.py`

**导入更新**：
```python
# 旧
from app.services.notification_service import NotificationService

# 新
from app.services.notification_internal_service import NotificationInternalService
from app.services.notification_external_service import NotificationExternalService
```

**调用更新**（3处）：
```python
# 旧：直接创建 NotificationExternal 实例
log = NotificationExternal(...)
db.add(log)
await db.commit()

# 新：使用 NotificationExternalService
log_data = NotificationExternalCreate(...)
log = await NotificationExternalService.create_log(db, log_data)
```

**删除方法**：
- ❌ `get_dispatch_statistics()` 方法（Line 499-608，共 110 行）
  - 迁移至 `NotificationExternalService.get_statistics()`

**职责收窄**：
- 专注于事件调度和消息分发
- 不再承担数据查询统计功能

---

#### `api/v1/notifications.py`

**导入更新**：
```python
# 旧
from app.services.notification_service import NotificationService

# 新
from app.services.notification_internal_service import NotificationInternalService
from app.services.notification_external_service import NotificationExternalService
```

**站内消息 API**（12 处调用）：
```python
# 所有 NotificationService 改为 NotificationInternalService
count = await NotificationInternalService.get_unread_count(db, current_user.id)
notifications, total = await NotificationInternalService.get_user_notifications(...)
notification = await NotificationInternalService.mark_as_read(...)
# ... 等
```

**站外消息 API**（2 处新增/修改）：
```python
# 旧：直接 SQL 查询（Line 326-364）
from sqlalchemy import select, func, and_
from app.models.notification import NotificationExternal
stmt = select(NotificationExternal).where(...)
result = await db.execute(stmt)

# 新：使用 Service 层
logs, total = await NotificationExternalService.get_user_logs(
    db, user_id, skip, limit, status, channel_type, ...
)
```

---

### 4. 兼容性别名

#### `notification_service.py`（新建）

```python
# -*- coding: utf-8 -*-
"""
通知服务 - 向后兼容别名

此文件用于保持向后兼容性，新代码请直接使用：
- NotificationInternalService（站内消息）
- NotificationExternalService（站外消息）
"""
from app.services.notification_internal_service import NotificationInternalService as NotificationService

__all__ = ["NotificationService"]
```

**用途**：
- 保持旧代码无需修改（如测试文件）
- 逐步迁移，避免一次性修改所有导入

---

## 🧪 测试验证

### 导入测试
```bash
$ python -c "
from app.services.notification_internal_service import NotificationInternalService
from app.services.notification_external_service import NotificationExternalService
from app.services.notification_dispatch_service import NotificationDispatchService
print('All services imported successfully!')
"
```

**结果**：✅ 所有服务导入成功

### API 测试
```bash
$ python -c "from app.api.v1 import notifications; print('API routes loaded')"
```

**结果**：✅ API 路由加载成功

### 兼容性测试
```bash
$ python -c "
from app.services.notification_service import NotificationService
print('Compatibility alias works:', NotificationService.__name__)
"
```

**结果**：✅ 兼容性别名正常工作（NotificationInternalService）

---

## 🆕 新增功能

### 1. 通知全局配置

**初始化脚本**：`scripts/init_notification_settings.py`

**配置项**（16 项）：
```python
category = "notification"

# 基础配置
notification.default_language           # "zh-CN"
notification.retention_days             # "30"
notification.max_message_length         # "1000"
notification.deduplication_window       # "300"
notification.max_retry_count            # "3"
notification.enable_system_messages     # "true"

# Telegram 配置
notification.telegram.default_parse_mode    # "Markdown"
notification.telegram.disable_notification  # "false"

# Email 配置
notification.email.smtp_timeout         # "30"
notification.email.use_tls              # "true"

# Webhook 配置
notification.webhook.default_method     # "POST"
notification.webhook.timeout            # "30"
notification.webhook.follow_redirects   # "true"

# 渠道通用配置
notification.channel_timeout                    # "30"
notification.batch_send_enabled                 # "false"
notification.consecutive_failures_threshold     # "5"
```

**使用方式**：
```bash
# 初始化配置
python scripts/init_notification_settings.py

# 查看当前配置
python scripts/init_notification_settings.py --show
```

### 2. 站外消息历史 API

**新增接口**：

#### `GET /api/v1/notifications/external`
获取站外消息历史列表

**参数**：
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20）
- `status`: 状态筛选（pending/sent/failed）
- `channel_type`: 渠道类型（telegram/email/webhook）
- `notification_type`: 通知类型
- `start_date`: 开始日期
- `end_date`: 结束日期

**响应**：
```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "userId": 1,
      "notificationType": "subscription_matched",
      "channelId": 1,
      "channelType": "telegram",
      "title": "订阅匹配",
      "content": "您订阅的资源已找到",
      "status": "sent",
      "retryCount": 0,
      "sentAt": "2025-11-30T10:30:00+08:00",
      "createdAt": "2025-11-30T10:30:00+08:00"
    }
  ]
}
```

#### `GET /api/v1/notifications/external/{id}`
获取单个站外消息详情

**响应**：同上单个对象

---

## 📋 数据模型

### notification_external 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户 ID |
| notification_type | VARCHAR(50) | 通知类型 |
| channel_id | INTEGER | 渠道 ID（外键） |
| channel_type | VARCHAR(30) | 渠道类型 |
| title | VARCHAR(200) | 标题 |
| content | TEXT | 内容 |
| status | VARCHAR(20) | 状态（pending/sent/failed） |
| retry_count | INTEGER | 重试次数 |
| error_message | TEXT | 错误信息 |
| sent_at | DATETIME | 发送时间 |
| response_data | JSON | 渠道返回数据 |
| extra_data | JSON | 扩展数据 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### notification_internal 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户 ID（NULL 表示广播） |
| notification_type | VARCHAR(50) | 通知类型 |
| title | VARCHAR(200) | 标题 |
| content | TEXT | 内容 |
| priority | VARCHAR(20) | 优先级（low/normal/high/urgent） |
| status | VARCHAR(20) | 状态（unread/read/archived） |
| related_type | VARCHAR(50) | 关联资源类型 |
| related_id | INTEGER | 关联资源 ID |
| extra_data | JSON | 扩展数据 |
| read_at | DATETIME | 阅读时间 |
| expires_at | DATETIME | 过期时间 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## 🔄 迁移指南

### 对于现有代码

**如果使用了 `NotificationService`**：
```python
# 方案 A：继续使用别名（推荐，向后兼容）
from app.services.notification_service import NotificationService
# 无需修改，兼容性别名会自动指向 NotificationInternalService

# 方案 B：迁移到新名称（推荐，语义更清晰）
from app.services.notification_internal_service import NotificationInternalService
# 将所有 NotificationService 替换为 NotificationInternalService
```

**如果需要站外消息功能**：
```python
# 新增导入
from app.services.notification_external_service import NotificationExternalService

# 使用示例
logs, total = await NotificationExternalService.get_user_logs(db, user_id, skip, limit)
stats = await NotificationExternalService.get_statistics(db, user_id, days=7)
```

---

## 📚 API 文档

### Swagger UI
访问：`http://localhost:8000/docs`

### 核心接口

#### 站内消息
- `GET /api/v1/notifications` - 获取站内消息列表
- `GET /api/v1/notifications/{id}` - 获取消息详情
- `PUT /api/v1/notifications/{id}/read` - 标记已读
- `PUT /api/v1/notifications/read-all` - 全部已读
- `DELETE /api/v1/notifications/{id}` - 删除消息

#### 站外消息
- `GET /api/v1/notifications/external` - 获取站外消息历史
- `GET /api/v1/notifications/external/{id}` - 获取详情

#### 系统设置
- `GET /api/v1/system-settings?category=notification` - 获取通知配置
- `POST /api/v1/system-settings/{category}/{key}/upsert` - 保存配置

---

## ✅ 验收标准

### 功能完整性
- [x] NotificationExternalService 创建完成
- [x] NotificationInternalService 重命名完成
- [x] NotificationDispatchService 调整完成
- [x] API 层更新完成
- [x] 兼容性别名创建完成
- [x] 通知全局配置初始化
- [x] 站外消息历史 API

### 测试通过
- [x] 所有 Service 导入成功
- [x] API 路由加载成功
- [x] 兼容性别名正常工作
- [x] Backend 应用启动成功

### 代码质量
- [x] 无 Python 语法错误
- [x] 符合架构分层原则
- [x] 职责划分清晰
- [x] 命名准确规范

---

## 🚀 下一步

### 前端配套任务
详见：`frontend/FRONTEND_REFACTORING_TASK.md`

**主要任务**：
1. 重构 `/notifications` 页面（简化为消息中心）
2. 重构 `/settings?tab=notifications` 页面（配置管理）
3. 添加跨页面导航优化

**预计工作量**：3-4.5 小时

---

## 📞 联系方式

**重构负责人**：Claude Code
**创建日期**：2025-11-30
**版本**：v1.0

---

## 附录

### A. 文件变更清单

| 文件 | 操作 | 行数变化 |
|------|------|---------|
| `services/notification_external_service.py` | 新增 | +298 |
| `services/notification_service.py` | 重命名 | → notification_internal_service.py |
| `services/notification_service.py` | 新建别名 | +10 |
| `services/notification_dispatch_service.py` | 修改 | -110, +改动 |
| `api/v1/notifications.py` | 修改 | -30, +65 |
| `scripts/init_notification_settings.py` | 新增 | +200 |
| **总计** | - | **+563 行新增, -140 行删除** |

### B. 关键常量定义

**文件**：`app/constants/notification.py`

```python
# 发送状态
NOTIFICATION_SEND_STATUS_PENDING = "pending"
NOTIFICATION_SEND_STATUS_SENT = "sent"
NOTIFICATION_SEND_STATUS_FAILED = "failed"

# 站内消息状态
NOTIFICATION_STATUS_UNREAD = "unread"
NOTIFICATION_STATUS_READ = "read"
NOTIFICATION_STATUS_ARCHIVED = "archived"

# 渠道类型
NOTIFICATION_CHANNEL_TELEGRAM = "telegram"
NOTIFICATION_CHANNEL_EMAIL = "email"
NOTIFICATION_CHANNEL_WEBHOOK = "webhook"

# 优先级
NOTIFICATION_PRIORITY_LOW = "low"
NOTIFICATION_PRIORITY_NORMAL = "normal"
NOTIFICATION_PRIORITY_HIGH = "high"
NOTIFICATION_PRIORITY_URGENT = "urgent"
```
