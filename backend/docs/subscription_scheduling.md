# 订阅调度架构说明

## 设计原则

订阅系统采用**统一调度架构**：
- **单一全局任务**：一个定时任务负责扫描所有订阅
- **订阅独立配置**：每个订阅维护自己的检查间隔和规则
- **按需执行**：只检查到期的订阅，不浪费资源

## 架构图

```
┌─────────────────────────────────────┐
│   全局定时任务（ScheduledTask）      │
│   - 任务类型: subscription_check     │
│   - 调度间隔: 5分钟（可配置）          │
│   - handler_params: {}（空=所有）     │
└──────────────┬──────────────────────┘
               │
               ↓ 每5分钟执行一次
┌─────────────────────────────────────┐
│  SubscriptionCheckHandler            │
│  .check_all_subscriptions()          │
└──────────────┬──────────────────────┘
               │
               ↓ SQL 查询
┌─────────────────────────────────────┐
│  SELECT * FROM subscriptions         │
│  WHERE is_active = true              │
│    AND status = 'active'             │
│    AND next_check_at <= NOW()        │
└──────────────┬──────────────────────┘
               │
               ↓ 找到到期订阅
┌─────────────────────────────────────┐
│  订阅1: check_interval=60分钟        │
│  订阅2: check_interval=120分钟       │
│  订阅3: check_interval=30分钟        │
└──────────────┬──────────────────────┘
               │
               ↓ 逐个检查
         更新 next_check_at
```

## 关键字段

### Subscription 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `check_interval` | INTEGER | 检查间隔（分钟），范围：60~10080（1小时~7天） |
| `next_check_at` | DATETIME | 下次检查时间，由系统自动计算 |
| `last_check_at` | DATETIME | 上次检查时间，用于统计 |
| `is_active` | BOOLEAN | 是否激活，暂停时为 false |
| `status` | VARCHAR | 订阅状态：active/paused/completed/cancelled |

### ScheduledTask 表字段

| 字段 | 值 | 说明 |
|------|------|------|
| `task_type` | `subscription_check` | 任务类型 |
| `task_name` | `订阅自动检查（全局）` | 任务名称 |
| `schedule_type` | `interval` | 调度类型：间隔 |
| `schedule_config` | `{"interval": 5, "unit": "minutes"}` | 每5分钟 |
| `handler_params` | `{}` | 空参数 = 检查所有到期订阅 |

## 执行流程

### 1. 系统启动

```python
# app/main.py -> lifespan
async with async_session_local() as db:
    await initialize_system(engine, db)  # 初始化系统

# app/core/init.py -> initialize_system
await init_system_tasks()  # 初始化系统任务

# app/core/init_system.py -> init_system_tasks
await init_subscription_check_task(db)  # 创建全局订阅检查任务
```

### 2. 任务调度

```python
# 每5分钟，APScheduler 触发
scheduler_manager._execute_scheduled_task(task_id)
  ↓
# 执行处理器
SubscriptionCheckHandler.check_all_subscriptions(db)
  ↓
# 查询到期订阅
subscriptions = await SubscriptionService.get_active_subscriptions_for_check(db)
# WHERE next_check_at <= NOW()
  ↓
# 逐个检查
for subscription in subscriptions:
    await SubscriptionCheckHandler.check_subscription(db, subscription.id)
```

### 3. 检查完成

```python
# 更新订阅统计
subscription.last_check_at = now()
subscription.next_check_at = now() + timedelta(minutes=check_interval)
subscription.total_checks += 1

# 记录检查日志
SubscriptionCheckLogService.create_log(...)
```

## 配置说明

### 环境变量配置

```bash
# .env 文件
SUBSCRIPTION_CHECK_INTERVAL_MINUTES=5  # 全局扫描间隔
```

**说明**：
- 这个值是全局任务的扫描频率，不是单个订阅的检查间隔
- 建议设置为 5 分钟，可以及时响应到期订阅
- 不建议设置太小（<1分钟），会增加数据库压力

### 订阅检查间隔

每个订阅创建时可以设置自己的 `check_interval`：
- 最小：60 分钟
- 最大：10080 分钟（7天）
- 默认：60 分钟

```json
{
  "checkInterval": 120,  // 2小时检查一次
  "title": "某剧集订阅"
}
```

## 优势分析

### vs. 一对一映射（每个订阅一个 ScheduledTask）

| 特性 | 统一调度（当前） | 一对一映射 |
|------|----------------|-----------|
| 任务数量 | 1 个 | N 个（N=订阅数） |
| APScheduler 负载 | 低 | 高（上千订阅时） |
| 数据库表大小 | 小 | 大 |
| 修改订阅间隔 | 立即生效 | 需要更新 ScheduledTask |
| 删除订阅 | 简单 | 需要同步删除 ScheduledTask |
| 职责分离 | 清晰（订阅=业务，任务=调度） | 模糊 |

### vs. 双层调度（全局任务每次检查所有订阅）

| 特性 | 统一调度（当前） | 双层调度 |
|------|----------------|---------|
| 扫描效率 | 高（只查询到期订阅） | 低（每次扫描所有） |
| 数据库压力 | 小 | 大 |
| 调度精度 | 高（±5分钟） | 取决于全局间隔 |
| 实现复杂度 | 简单 | 简单 |

## 手动触发

除了自动调度，还支持手动触发单个订阅检查：

```bash
POST /api/v1/subscriptions/{id}/check
```

这个 API 会：
1. 立即检查该订阅
2. 更新 `next_check_at`
3. 记录检查日志

## 监控建议

### 查看调度任务状态

```sql
-- 查看全局订阅检查任务
SELECT * FROM scheduled_tasks
WHERE task_type = 'subscription_check';

-- 查看最近的任务执行
SELECT * FROM task_executions
WHERE task_type = 'subscription_check'
ORDER BY created_at DESC
LIMIT 10;
```

### 查看订阅状态

```sql
-- 查看即将检查的订阅
SELECT id, title, next_check_at, check_interval
FROM subscriptions
WHERE is_active = true
  AND status = 'active'
  AND next_check_at <= datetime('now', '+10 minutes')
ORDER BY next_check_at;

-- 查看长时间未检查的订阅
SELECT id, title, last_check_at, next_check_at
FROM subscriptions
WHERE is_active = true
  AND last_check_at < datetime('now', '-1 day')
ORDER BY last_check_at;
```

## 故障排查

### 问题：订阅没有自动检查

**检查步骤**：

1. 确认全局任务存在且已启用
```sql
SELECT * FROM scheduled_tasks
WHERE task_type = 'subscription_check';
```

2. 检查调度器是否运行
```python
# 查看日志
tail -f backend/data/logs/nasfusion.log | grep "订阅检查"
```

3. 检查订阅的 `next_check_at`
```sql
SELECT id, title, next_check_at, is_active, status
FROM subscriptions
WHERE id = 1;
```

### 问题：订阅检查频率不对

检查两个配置：
1. 全局扫描间隔：`SUBSCRIPTION_CHECK_INTERVAL_MINUTES`（默认5分钟）
2. 订阅检查间隔：`subscriptions.check_interval`（每个订阅独立）

例如：
- 全局任务每 5 分钟扫描一次
- 订阅A的 `check_interval = 120`（2小时）
- 订阅A会在 `next_check_at` 到达后的 0~5 分钟内被检查

## 未来扩展

可以考虑的优化：
1. 支持订阅优先级队列（高优先级订阅优先检查）
2. 支持订阅分组批量检查
3. 支持动态调整全局扫描频率（根据订阅数量）
4. 支持订阅检查结果缓存（减少重复查询）

---

**最后更新**: 2025-11-23
**版本**: v1.0
