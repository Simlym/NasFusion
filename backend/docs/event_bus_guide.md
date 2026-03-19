# NasFusion 事件总线系统指南

> 📅 最后更新：2025-12-07
> 📝 版本：v2.0
> 🎯 目标：解耦业务逻辑与事件处理，提升系统可扩展性
> 🔄 重大更新：分离业务事件常量与通知系统配置

---

## 📖 目录

1. [系统概述](#系统概述)
2. [核心架构](#核心架构)
3. [核心组件](#核心组件)
4. [使用指南](#使用指南)
5. [已集成事件](#已集成事件)
6. [实际案例](#实际案例)
7. [最佳实践](#最佳实践)
8. [扩展指南](#扩展指南)
9. [常见问题](#常见问题)

---

## 系统概述

### 什么是事件总线？

事件总线（Event Bus）是一种**发布-订阅模式**的消息传递机制，用于解耦系统中的不同模块。

**核心思想**：
```
业务服务 → 发布事件 → 事件总线 → 分发到监听器 → 执行具体操作
```

### 为什么需要事件总线？

#### ❌ 传统方式的问题（紧耦合）

```python
# 业务代码中直接调用通知服务
from app.services.notification_dispatch_service import NotificationDispatchService

async def complete_download(db, task):
    # 下载完成逻辑
    ...

    # ❌ 业务代码强依赖通知服务
    await NotificationDispatchService.dispatch_event(db, ...)

    # ❌ 如果还需要记录审计日志，继续添加
    await AuditLogService.log_event(db, ...)

    # ❌ 如果还需要更新用户积分，继续添加
    await UserPointsService.add_points(db, ...)
```

**问题**：
1. **高耦合**：业务代码需要知道所有关联系统
2. **难扩展**：每增加一个功能，都要修改业务代码
3. **难测试**：需要 mock 多个服务
4. **性能差**：同步等待所有操作完成，阻塞业务流程

#### ✅ 事件总线方式（解耦）

```python
# 业务代码只发布事件
from app.constants.event import EVENT_DOWNLOAD_COMPLETED
from app.events.bus import event_bus

async def complete_download(db, task):
    # 下载完成逻辑
    ...

    # ✅ 只发布事件，不关心谁处理
    await event_bus.publish(EVENT_DOWNLOAD_COMPLETED, {
        "user_id": task.user_id,
        "task_id": task.id,
        "file_name": task.torrent_name
    })

    # 业务代码结束，后续由监听器自动处理
```

**优势**：
1. **低耦合**：业务代码只依赖事件总线
2. **易扩展**：新增监听器无需修改业务代码
3. **易测试**：只需 mock 事件总线
4. **高性能**：异步执行，不阻塞业务流程

---

## 核心架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                       业务服务层                              │
│  DownloadTaskService  │  SubscriptionService  │  MediaService │
└───────────────┬───────────────────┬─────────────────┬────────┘
                │                   │                 │
                │ publish()         │ publish()       │ publish()
                ▼                   ▼                 ▼
        ┌───────────────────────────────────────────────┐
        │           Event Bus（事件总线）                │
        │  - 管理监听器注册                              │
        │  - 异步分发事件                                │
        │  - 并发执行监听器                              │
        └───────────────────┬───────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  Notification│ │    Audit     │ │   Metrics    │
    │   Listener   │ │   Listener   │ │   Listener   │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           ▼                ▼                ▼
    发送通知         记录日志         收集指标
```

### 数据流

```
1. 业务代码 → event_bus.publish("download_completed", {...})
                    ↓
2. 事件总线接收事件 → 查找订阅此事件的监听器
                    ↓
3. 并发执行所有监听器（异步，不阻塞）
                    ↓
4. 监听器1：NotificationListener → 发送通知
   监听器2：AuditListener → 记录审计日志
   监听器3：MetricsListener → 收集性能指标
```

---

## 核心组件

### 1. EventBus（事件总线核心）

**文件位置**：`app/services/event_bus.py`

**主要方法**：

```python
class EventBus:
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""

    async def publish(self, event_type: str, event_data: Dict, wait: bool = False):
        """发布事件"""

    def start(self):
        """启动事件总线"""

    def stop(self):
        """停止事件总线"""
```

**关键特性**：
- ✅ 支持多监听器订阅同一事件
- ✅ 异步并发执行所有监听器
- ✅ 监听器执行异常不影响其他监听器
- ✅ 提供统计信息（事件类型数、监听器数）

---

### 2. EventBusManager（生命周期管理器）

**文件位置**：`app/services/event_bus_manager.py`

**主要方法**：

```python
class EventBusManager:
    async def start(self):
        """启动事件总线并注册所有监听器"""

    async def stop(self):
        """停止事件总线"""

    def get_stats(self):
        """获取统计信息"""
```

**职责**：
- 管理事件总线的启动和停止
- 自动注册所有监听器
- 集成到应用生命周期（`main.py` 的 `lifespan`）

---

### 3. NotificationListener（通知监听器）

**文件位置**：`app/listeners/notification_listener.py`

**核心函数**：

```python
async def handle_notification_event(event_type: str, event_data: Dict[str, Any]):
    """
    处理通知事件

    接收事件总线发布的事件，调度通知发送。
    """
    async with async_session_local() as db:
        await NotificationDispatchService.dispatch_event(
            db,
            event_type=event_type,
            event_data=event_data,
            user_id=event_data.get("user_id"),
            broadcast=event_data.get("broadcast", False)
        )
```

**职责**：
- 监听所有通知相关事件（23种事件类型）
- 自动创建数据库会话
- 调用 `NotificationDispatchService` 发送通知

---

## 使用指南

### 1. 如何发布事件

#### 基本用法

```python
from app.services.event_bus import event_bus

# 发布单用户通知事件
await event_bus.publish("download_completed", {
    "user_id": 1,                        # 必需：用户ID
    "media_name": "复仇者联盟4",          # 业务数据
    "size_gb": 15.5,
    "related_type": "download_task",     # 可选：关联资源类型
    "related_id": 123                    # 可选：关联资源ID
})
```

#### 广播消息

```python
# 发布广播通知（发送给所有用户）
await event_bus.publish("system_error", {
    "broadcast": True,                   # 必需：标记为广播
    "title": "系统异常",
    "content": "检测到系统异常，请尽快处理"
})
```

#### 同步等待（测试场景）

```python
# 等待所有监听器执行完成
await event_bus.publish("critical_event", {...}, wait=True)
```

---

### 2. 如何添加新事件类型

#### 步骤 1：在常量文件中定义事件类型

**文件位置**：`app/constants/notification.py`

```python
# 添加新事件类型常量
NOTIFICATION_EVENT_YOUR_NEW_EVENT = "your_new_event"

# 添加到事件列表
NOTIFICATION_EVENTS = [
    # ... 现有事件
    NOTIFICATION_EVENT_YOUR_NEW_EVENT,
]

# （可选）设置事件优先级
EVENT_PRIORITY_MAPPING = {
    # ... 现有映射
    NOTIFICATION_EVENT_YOUR_NEW_EVENT: NOTIFICATION_PRIORITY_NORMAL,
}
```

#### 步骤 2：在业务代码中发布事件

```python
from app.constants.notification import NOTIFICATION_EVENT_YOUR_NEW_EVENT
from app.services.event_bus import event_bus

async def your_business_function(db, ...):
    # 业务逻辑
    ...

    # 发布事件
    await event_bus.publish(
        NOTIFICATION_EVENT_YOUR_NEW_EVENT,
        {
            "user_id": user_id,
            "custom_field": "custom_value",
            "related_type": "your_resource",
            "related_id": resource_id,
        }
    )
```

#### 步骤 3：创建通知模板（可选）

在前端"通知模板管理"页面创建对应的通知模板，用于渲染通知内容。

**就这么简单！** 通知监听器会自动处理所有在 `NOTIFICATION_EVENTS` 中定义的事件。

---

### 3. 如何创建自定义监听器

#### 场景：添加审计日志监听器

**步骤 1：创建监听器文件**

```python
# app/listeners/audit_listener.py
import logging
from typing import Any, Dict

from app.core.database import async_session_local
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)

async def handle_audit_event(event_type: str, event_data: Dict[str, Any]):
    """处理审计日志事件"""
    async with async_session_local() as db:
        try:
            await AuditLogService.log_event(
                db,
                event_type=event_type,
                user_id=event_data.get("user_id"),
                action=event_type,
                details=event_data
            )
            logger.info(f"审计日志已记录: {event_type}")
        except Exception as e:
            logger.exception(f"记录审计日志失败: {e}")
```

**步骤 2：注册监听器**

在 `app/services/event_bus_manager.py` 中添加注册逻辑：

```python
async def _register_listeners(self):
    # ... 现有注册逻辑

    # 注册审计监听器
    await self._register_audit_listener()

async def _register_audit_listener(self):
    """注册审计监听器"""
    from app.listeners.audit_listener import handle_audit_event

    # 只监听需要审计的事件
    audit_events = [
        "download_completed",
        "subscription_matched",
        "media_organized",
        # ... 其他需要审计的事件
    ]

    for event_type in audit_events:
        event_bus.subscribe(event_type, handle_audit_event)

    logger.info(f"✅ 审计监听器已注册: {len(audit_events)} 个事件类型")
```

---

## 已集成事件

### 迁移的事件（4个）

| 服务 | 事件类型 | 文件位置 | 触发场景 |
|------|---------|---------|---------|
| 下载任务服务 | `download_completed` | `download_task_service.py:610` | 下载进度达到 100% |
| 下载任务服务 | `download_failed` | `download_task_service.py:645` | 下载器返回错误 |
| 订阅检查服务 | `subscription_matched` | `subscription_check_handler.py:337` | 订阅匹配到资源 |
| 订阅检查服务 | `subscription_downloaded` | `subscription_check_handler.py:385` | 订阅自动下载触发 |

---

### 新增的事件（5个）

| 服务 | 事件类型 | 文件位置 | 触发场景 |
|------|---------|---------|---------|
| 媒体文件服务 | `media_scan_completed` | `media_file_service.py:338` | 目录扫描完成 |
| PT 站点服务 | `site_sync_completed` | `pt_site_service.py:219` | 站点元数据同步完成 |
| 任务调度系统 | `task_completed` | `scheduler_manager.py:236` | 调度任务执行成功 |
| 任务调度系统 | `task_failed` | `scheduler_manager.py:276` | 调度任务执行失败 |

---

### 完整事件清单（23个）

#### 订阅相关（4个）
- `subscription_matched` - 订阅匹配到资源
- `subscription_downloaded` - 订阅自动下载
- `subscription_completed` - 订阅完成
- `subscription_no_resource` - 订阅无资源

#### 下载相关（4个）
- `download_started` - 下载开始
- `download_completed` - 下载完成 ✅
- `download_failed` - 下载失败 ✅
- `download_paused` - 下载暂停

#### 资源相关（3个）
- `resource_free_promotion` - 免费促销资源
- `resource_2x_promotion` - 2倍上传促销
- `resource_high_quality` - 高质量资源

#### PT 站点相关（3个）
- `site_connection_failed` - 站点连接失败
- `site_auth_expired` - 站点认证过期
- `site_sync_completed` - 站点同步完成 ✅

#### 媒体文件相关（3个）
- `media_scan_completed` - 媒体扫描完成 ✅
- `media_organized` - 媒体整理完成
- `media_metadata_scraped` - 元数据刮削完成

#### 任务相关（2个）
- `task_failed` - 任务失败 ✅
- `task_completed` - 任务完成 ✅

#### 系统相关（4个）
- `system_error` - 系统错误
- `disk_space_low` - 磁盘空间不足
- `user_login_anomaly` - 异常登录
- `system_update_available` - 系统更新可用

---

## 实际案例

### 案例 1：下载完成通知

**场景**：用户下载任务完成后，发送通知告知用户。

**原实现（紧耦合）**：

```python
# app/services/download_task_service.py
async def _send_completion_notification(db: AsyncSession, task: DownloadTask):
    from app.services.notification_dispatch_service import NotificationDispatchService

    # ❌ 直接调用通知服务
    await NotificationDispatchService.dispatch_event(
        db,
        event_type="download_completed",
        event_data={...},
        user_id=task.user_id
    )
```

**新实现（解耦）**：

```python
# app/services/download_task_service.py
async def _send_completion_notification(db: AsyncSession, task: DownloadTask):
    from app.services.event_bus import event_bus

    # ✅ 只发布事件
    await event_bus.publish("download_completed", {
        "user_id": task.user_id,
        "media_name": task.torrent_name,
        "size_gb": round(task.file_size / (1024**3), 2),
        "duration": "15分钟",
        "related_type": "download_task",
        "related_id": task.id
    })
```

**效果**：
- ✅ 业务代码不再依赖通知服务
- ✅ 如果需要添加审计日志，只需添加监听器，无需修改业务代码

---

### 案例 2：订阅匹配通知

**场景**：订阅检查到匹配资源时，通知用户。

**实现代码**：

```python
# app/services/subscription_check_handler.py
async def _send_match_notification(
    db: AsyncSession,
    subscription: Subscription,
    pt_resource: PTResource
):
    from app.services.event_bus import event_bus

    await event_bus.publish("subscription_matched", {
        "user_id": subscription.user_id,
        "media_name": subscription.title,
        "quality": pt_resource.resolution,
        "size_gb": round(pt_resource.size / (1024**3), 2),
        "site_name": pt_resource.site.name,
        "promotion_type": pt_resource.promotion_type,
        "related_type": "pt_resource",
        "related_id": pt_resource.id,
        "subscription_id": subscription.id
    })
```

---

### 案例 3：媒体扫描完成（新增）

**场景**：后台任务扫描媒体目录完成后，通知用户。

**实现代码**：

```python
# app/services/media_file_service.py
async def scan_directory(db: AsyncSession, directory: str, ...):
    # ... 扫描逻辑

    if media_files:
        from app.services.event_bus import event_bus

        # 发布广播事件
        await event_bus.publish("media_scan_completed", {
            "broadcast": True,  # 广播给所有用户
            "directory": directory,
            "files_created": len(media_files),
            "is_media_library": is_media_library,
            "related_type": "media_scan",
            "related_id": None
        })
```

---

## 最佳实践

### 1. 事件数据格式规范

#### 必需字段

```python
{
    "user_id": 1,              # 单用户通知时必需
    # 或
    "broadcast": True,         # 广播消息时必需
}
```

#### 推荐字段

```python
{
    "user_id": 1,

    # 关联资源（用于通知跳转）
    "related_type": "download_task",  # pt_resource, subscription, media_file 等
    "related_id": 123,

    # 业务数据（用于模板渲染）
    "media_name": "复仇者联盟4",
    "size_gb": 15.5,
    "quality": "1080p",
    ...
}
```

---

### 2. 错误处理策略

#### 业务代码中的错误处理

```python
async def your_business_function(db, ...):
    # 业务逻辑
    ...

    try:
        # 发布事件（不应阻塞业务流程）
        await event_bus.publish("event_type", {...})
    except Exception as e:
        # 记录日志，但不中断业务流程
        logger.exception(f"发布事件失败: {e}")
```

#### 监听器中的错误处理

```python
async def handle_your_event(event_type: str, event_data: Dict):
    try:
        # 处理逻辑
        ...
    except Exception as e:
        # 记录详细错误日志
        logger.exception(f"处理事件失败: {event_type}, 数据: {event_data}, 错误: {e}")
        # 不抛出异常，避免影响其他监听器
```

---

### 3. 性能优化建议

#### 使用异步发布（默认）

```python
# ✅ 推荐：异步发布，不等待监听器执行
await event_bus.publish("event_type", {...})
# 代码立即继续执行
```

#### 避免同步等待

```python
# ❌ 不推荐：同步等待，阻塞业务流程
await event_bus.publish("event_type", {...}, wait=True)
# 只在测试或关键事件时使用
```

#### 监听器优化

```python
async def handle_event(event_type, event_data):
    # ✅ 尽早创建数据库会话
    async with async_session_local() as db:
        # ✅ 避免复杂查询
        # ✅ 使用批量操作
        # ✅ 设置合理的超时时间
        ...
```

---

## 扩展指南

### 1. 添加审计监听器

**目标**：记录所有关键操作到审计日志表。

**实现步骤**：

1. **创建监听器**（`app/listeners/audit_listener.py`）：

```python
import logging
from typing import Any, Dict

from app.core.database import async_session_local

logger = logging.getLogger(__name__)

async def handle_audit_event(event_type: str, event_data: Dict[str, Any]):
    """记录审计日志"""
    async with async_session_local() as db:
        try:
            from app.models.audit_log import AuditLog

            log = AuditLog(
                event_type=event_type,
                user_id=event_data.get("user_id"),
                action=event_type,
                details=event_data,
                ip_address=event_data.get("ip_address"),
                user_agent=event_data.get("user_agent")
            )

            db.add(log)
            await db.commit()

            logger.debug(f"审计日志已记录: {event_type}")

        except Exception as e:
            logger.exception(f"记录审计日志失败: {e}")
```

2. **注册监听器**（在 `event_bus_manager.py` 中）：

```python
async def _register_listeners(self):
    await self._register_notification_listener()
    await self._register_audit_listener()  # 新增

async def _register_audit_listener(self):
    from app.listeners.audit_listener import handle_audit_event

    # 只监听需要审计的事件
    audit_events = [
        "download_completed",
        "subscription_matched",
        "media_organized",
    ]

    for event_type in audit_events:
        event_bus.subscribe(event_type, handle_audit_event)

    logger.info(f"✅ 审计监听器已注册: {len(audit_events)} 个事件")
```

---

### 2. 添加指标监听器

**目标**：收集性能指标到 Prometheus/Grafana。

**实现步骤**：

1. **创建监听器**（`app/listeners/metrics_listener.py`）：

```python
import logging
from typing import Any, Dict
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# 定义指标
event_counter = Counter('nasfusion_events_total', 'Total events', ['event_type'])
event_duration = Histogram('nasfusion_event_duration_seconds', 'Event processing time', ['event_type'])

async def handle_metrics_event(event_type: str, event_data: Dict[str, Any]):
    """收集性能指标"""
    try:
        # 增加事件计数
        event_counter.labels(event_type=event_type).inc()

        # 记录事件处理时长（如果有）
        if 'duration' in event_data:
            event_duration.labels(event_type=event_type).observe(event_data['duration'])

        logger.debug(f"指标已记录: {event_type}")

    except Exception as e:
        logger.exception(f"记录指标失败: {e}")
```

2. **注册监听器**（在 `event_bus_manager.py` 中）：

```python
async def _register_metrics_listener(self):
    from app.listeners.metrics_listener import handle_metrics_event
    from app.constants.notification import NOTIFICATION_EVENTS

    # 监听所有事件
    for event_type in NOTIFICATION_EVENTS:
        event_bus.subscribe(event_type, handle_metrics_event)

    logger.info(f"✅ 指标监听器已注册: {len(NOTIFICATION_EVENTS)} 个事件")
```

---

### 3. 添加 Webhook 监听器

**目标**：支持用户自定义 Webhook 回调。

**实现步骤**：

1. **创建监听器**（`app/listeners/webhook_listener.py`）：

```python
import logging
from typing import Any, Dict
import httpx

from app.core.database import async_session_local

logger = logging.getLogger(__name__)

async def handle_webhook_event(event_type: str, event_data: Dict[str, Any]):
    """发送 Webhook 通知"""
    async with async_session_local() as db:
        try:
            # 查询用户配置的 Webhook
            from app.models.webhook_config import WebhookConfig
            from sqlalchemy import select

            user_id = event_data.get("user_id")
            if not user_id:
                return

            result = await db.execute(
                select(WebhookConfig).where(
                    WebhookConfig.user_id == user_id,
                    WebhookConfig.is_active == True,
                    WebhookConfig.event_types.contains([event_type])
                )
            )
            webhooks = result.scalars().all()

            # 发送到所有配置的 Webhook
            async with httpx.AsyncClient() as client:
                for webhook in webhooks:
                    await client.post(
                        webhook.url,
                        json={
                            "event_type": event_type,
                            "event_data": event_data,
                            "timestamp": str(now())
                        },
                        timeout=5.0
                    )

            logger.debug(f"Webhook 已发送: {event_type} -> {len(webhooks)} 个端点")

        except Exception as e:
            logger.exception(f"发送 Webhook 失败: {e}")
```

2. **注册监听器**（在 `event_bus_manager.py` 中）：

```python
async def _register_webhook_listener(self):
    from app.listeners.webhook_listener import handle_webhook_event
    from app.constants.notification import NOTIFICATION_EVENTS

    for event_type in NOTIFICATION_EVENTS:
        event_bus.subscribe(event_type, handle_webhook_event)

    logger.info(f"✅ Webhook 监听器已注册: {len(NOTIFICATION_EVENTS)} 个事件")
```

---

## 常见问题

### Q1: 事件总线 vs 直接调用的区别？

**A**: 虽然调用代码看起来相似，但本质区别巨大：

| 对比维度 | 直接调用（紧耦合） | 事件总线（解耦） |
|---------|----------------|-----------------|
| **耦合度** | 强依赖通知服务 | 只依赖事件总线 |
| **执行方式** | 同步等待完成 | 异步后台处理 |
| **扩展性** | 需修改业务代码 | 添加监听器即可 |
| **数据库依赖** | 必须传递 db | 监听器自己管理 |
| **测试复杂度** | 需 mock 具体服务 | 只 mock 事件总线 |
| **性能影响** | 可能阻塞业务流程 | 不阻塞业务流程 |

**详细对比**：

```python
# ❌ 直接调用（紧耦合）
await NotificationDispatchService.dispatch_event(db, ...)
# - 业务代码必须导入通知服务
# - 必须传递数据库会话
# - 等待通知发送完成才继续执行
# - 新增功能需修改业务代码

# ✅ 事件总线（解耦）
await event_bus.publish("event_type", {...})
# - 业务代码只依赖事件总线
# - 不需要传递数据库会话
# - 发布后立即返回，不等待处理
# - 新增功能只需添加监听器
```

---

### Q2: 如何测试事件发布？

**A**: 使用 mock 事件总线验证事件发布。

**示例**：

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_download_complete_publishes_event():
    """测试下载完成时发布事件"""

    # Mock 事件总线
    with patch('app.services.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_publish:
        # 执行业务逻辑
        await download_service.complete_task(db, task_id)

        # 验证事件发布
        mock_publish.assert_called_once()

        # 验证事件类型
        call_args = mock_publish.call_args
        assert call_args[0][0] == "download_completed"

        # 验证事件数据
        event_data = call_args[0][1]
        assert event_data["user_id"] == 1
        assert event_data["media_name"] == "复仇者联盟4"
```

---

### Q3: 如何调试监听器？

**A**: 使用日志和断点调试。

**步骤 1：开启详细日志**

```python
# 在 app/core/logging.py 中设置日志级别
logging.getLogger("app.services.event_bus").setLevel(logging.DEBUG)
logging.getLogger("app.listeners").setLevel(logging.DEBUG)
```

**步骤 2：查看日志**

```bash
# 启动应用，查看日志输出
python -m app.main

# 日志示例：
# INFO: 已订阅事件: download_completed -> handle_notification_event
# INFO: 发布事件: download_completed, 监听器数量: 1
# DEBUG: 执行监听器: handle_notification_event for download_completed
# INFO: 通知事件处理完成: download_completed, 规则=1, 站内=1, 渠道=0
```

**步骤 3：使用断点调试**

在监听器函数中设置断点：

```python
async def handle_notification_event(event_type: str, event_data: Dict):
    import pdb; pdb.set_trace()  # 设置断点

    async with async_session_local() as db:
        ...
```

---

### Q4: 事件发布失败怎么办？

**A**: 事件总线已内置错误处理，监听器执行失败不会影响其他监听器。

**错误处理机制**：

```python
# 事件总线内部实现
async def _execute_handler(self, handler, event_type, event_data):
    try:
        await handler(event_type, event_data)
    except Exception as e:
        # 记录错误日志，但不抛出异常
        logger.exception(f"监听器执行失败: {handler.__name__}, 错误: {e}")
        # 继续执行其他监听器
```

**最佳实践**：

1. 在监听器内部捕获异常
2. 记录详细日志
3. 不抛出异常到事件总线

---

### Q5: 如何禁用某个监听器？

**A**: 在 `event_bus_manager.py` 中注释掉对应的注册代码。

**示例**：

```python
async def _register_listeners(self):
    # 注册通知监听器
    await self._register_notification_listener()

    # 注册审计监听器（暂时禁用）
    # await self._register_audit_listener()

    # 注册指标监听器
    await self._register_metrics_listener()
```

---

### Q6: 事件数据可以包含数据库对象吗？

**A**: 不推荐。建议只传递基本类型（int, str, dict, list）。

**❌ 不推荐**：

```python
await event_bus.publish("download_completed", {
    "task": task,  # SQLAlchemy 对象
})
```

**✅ 推荐**：

```python
await event_bus.publish("download_completed", {
    "task_id": task.id,           # 只传递 ID
    "task_name": task.torrent_name,
    "user_id": task.user_id,
})
```

**原因**：
- 监听器可能在不同的数据库会话中执行
- SQLAlchemy 对象可能已过期（expired）
- 序列化困难（如果需要持久化事件）

---

### Q7: 如何查看事件总线统计信息？

**A**: 调用 `event_bus_manager.get_stats()`。

**示例**：

```python
from app.services.event_bus_manager import event_bus_manager

stats = event_bus_manager.get_stats()
print(stats)

# 输出：
# {
#     "manager_started": True,
#     "is_started": True,
#     "event_types": ["download_completed", "subscription_matched", ...],
#     "total_event_types": 23,
#     "total_listeners": 23,
#     "listeners_by_event": {
#         "download_completed": 1,
#         "subscription_matched": 1,
#         ...
#     }
# }
```

---

## 总结

### 核心优势

1. **解耦**：业务代码与通知系统完全解耦
2. **异步**：不阻塞业务流程，提升性能
3. **可扩展**：新增监听器无需修改业务代码
4. **易测试**：只需 mock 事件总线
5. **统一管理**：所有事件集中管理，易于维护

### 使用建议

1. ✅ **所有新功能**都使用事件总线发布事件
2. ✅ **现有通知调用**逐步迁移到事件总线
3. ✅ **扩展新功能**（审计、指标）通过添加监听器实现
4. ❌ **不要**在监听器中执行耗时操作
5. ❌ **不要**在监听器中抛出异常

### 下一步计划

- [ ] 添加审计监听器
- [ ] 添加指标监听器（Prometheus）
- [ ] 添加 Webhook 监听器
- [ ] 完善事件数据验证（Pydantic Schema）
- [ ] 添加事件重试机制
- [ ] 添加事件持久化（事件溯源）

---

## 📋 重构历史

### v2.0 (2025-12-07) - 分离业务事件和通知系统

**背景问题**：
- 事件常量命名为 `NOTIFICATION_EVENT_*`，将事件与通知系统耦合
- 限制了事件的使用场景（审计、统计等处理器无法复用事件）
- 违反单一职责原则（事件应该是业务事实，而非处理方式）

**重构内容**：
1. 创建 `app/constants/event.py` - 业务事件常量模块
   - 使用 `EVENT_*` 命名规范（如 `EVENT_DOWNLOAD_COMPLETED`）
   - 事件值保持不变（如 `"download_completed"`），确保数据库兼容

2. 重构 `app/constants/notification.py` - 通知系统配置模块
   - 导入 `event.py` 中的业务事件
   - 保留事件优先级映射、默认启用事件等配置
   - 提供向后兼容别名（`NOTIFICATION_EVENT_*`）

3. 更新业务代码（12个文件）
   - `app/services/download_task_service.py`
   - `app/services/media_file_service.py`
   - `app/services/pt_site_service.py`
   - `app/services/scheduler_manager.py`
   - `app/services/subscription_check_handler.py`
   - `app/tasks/handlers/subscription_check_handler.py`
   - 其他相关文件

**代码示例**：

```python
# 重构前（耦合设计）
from app.constants.notification import NOTIFICATION_EVENT_DOWNLOAD_COMPLETED
await event_bus.publish(NOTIFICATION_EVENT_DOWNLOAD_COMPLETED, {...})

# 重构后（解耦设计）
from app.constants.event import EVENT_DOWNLOAD_COMPLETED
await event_bus.publish(EVENT_DOWNLOAD_COMPLETED, {...})
```

**架构优势**：

```
# 重构前：事件被通知系统"绑架"
NOTIFICATION_EVENT_DOWNLOAD_COMPLETED
    ↓ 只能发送通知？
notification_handler

# 重构后：事件成为业务领域的客观事实
EVENT_DOWNLOAD_COMPLETED
    ├── notification_handler (发送通知)
    ├── audit_handler (记录审计日志)
    ├── statistics_handler (更新统计数据)
    └── workflow_handler (触发后续任务)
```

**兼容性**：
- ✅ 事件值不变，数据库无需迁移
- ✅ 保留向后兼容别名，旧代码仍可运行
- ✅ 逐步废弃旧常量，完成平滑过渡

---

**文档维护者**: Claude Code
**创建日期**: 2025-11-29
**最后更新**: 2025-12-07
**版本**: v2.0
