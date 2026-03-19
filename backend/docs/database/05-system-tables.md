# 系统管理表

## 1. system_settings（系统配置）
**用途**：存储所有用户可配置的系统设置

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| key | VARCHAR(100) | UNIQUE, NOT NULL | 配置键 |
| value | TEXT |  | JSON格式值 |
| value_type | VARCHAR(20) | DEFAULT 'json' | 值类型：json/string/integer/boolean/float |
| category | VARCHAR(30) | NOT NULL | 分类：recommendation/sync/organizer/downloader/notification/ai/jellyfin/general |
| subcategory | VARCHAR(30) |  | 子分类 |
| description | TEXT |  | 配置说明 |
| is_user_configurable | BOOLEAN | DEFAULT TRUE | 是否允许用户修改 |
| is_sensitive | BOOLEAN | DEFAULT FALSE | 是否敏感信息，如API Key |
| default_value | TEXT |  | 默认值，JSON |
| validation_rules | JSON |  | 验证规则，JSON |
| ui_component | VARCHAR(30) |  | UI组件类型：slider/input/select/switch等 |
| ui_options | JSON |  | UI选项，JSON |
| version | VARCHAR(20) | DEFAULT '1.0' | 配置版本 |
| config_schema_version | VARCHAR(20) |  | 配置模式版本 |
| migration_history | JSON |  | 迁移历史 |
| environment | VARCHAR(20) | DEFAULT 'production' | 环境：development/staging/production |
| is_environment_specific | BOOLEAN | DEFAULT FALSE | 是否环境特定配置 |
| depends_on | JSON |  | 依赖的其他配置 |
| dependents | JSON |  | 被哪些配置依赖 |
| conflicts_with | JSON |  | 冲突的配置 |
| config_group | VARCHAR(50) |  | 配置组名称 |
| group_order | INTEGER | DEFAULT 0 | 组内排序 |
| group_collapsed | BOOLEAN | DEFAULT FALSE | UI中是否默认折叠 |
| hot_reload | BOOLEAN | DEFAULT FALSE | 是否支持热更新 |
| requires_restart | BOOLEAN | DEFAULT TRUE | 是否需要重启生效 |
| restart_services | JSON |  | 需要重启的服务列表 |
| change_notification | JSON |  | 变更通知配置 |
| is_template | BOOLEAN | DEFAULT FALSE | 是否为模板配置 |
| template_name | VARCHAR(100) |  | 模板名称 |
| template_category | VARCHAR(50) |  | 模板分类 |
| template_description | TEXT |  | 模板描述 |
| presets | JSON |  | 预设配置列表 |
| usage_stats | JSON |  | 使用统计 |
| performance_metrics | JSON |  | 性能指标 |
| user_id | INTEGER | FK → users | 用户特定配置 |
| scope | VARCHAR(20) | DEFAULT 'global' | 配置范围：global/user |
| is_inherited | BOOLEAN | DEFAULT TRUE | 是否继承全局配置 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(key)`
- `UNIQUE(scope, user_id, key)`
- `INDEX(category, subcategory)`
- `INDEX(user_id)`
- `INDEX(scope)`

---

## 2. scheduled_tasks（调度任务模板）
**用途**：存储系统中所有定时任务的调度配置和处理器定义

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| task_name | VARCHAR(255) | UNIQUE, NOT NULL | 任务名称，全局唯一标识 |
| task_type | VARCHAR(50) | NOT NULL | 任务类型：pt_sync/subscription_check/ai_recommendation/notification_send/scan_media/cleanup等 |
| enabled | BOOLEAN | DEFAULT TRUE | 是否启用该任务 |
| schedule_type | VARCHAR(50) | NOT NULL | 调度类型：cron/interval/one_time/manual |
| schedule_config | JSON |  | 调度配置，JSON格式，根据schedule_type不同而不同 |
| handler | VARCHAR(255) | NOT NULL | 处理器标识，对应后端处理函数路径 |
| handler_params | JSON |  | 处理器参数模板，JSON格式 |
| priority | INTEGER | DEFAULT 0 | 任务优先级，数值越大优先级越高 |
| next_run_at | TIMESTAMP |  | 下次计划执行时间 |
| last_run_at | TIMESTAMP |  | 最后执行时间 |
| last_run_status | VARCHAR(20) |  | 最后执行状态：success/failed/running |
| last_run_duration | INTEGER |  | 最后执行耗时，秒 |
| total_runs | INTEGER | DEFAULT 0 | 总执行次数 |
| success_runs | INTEGER | DEFAULT 0 | 成功执行次数 |
| failed_runs | INTEGER | DEFAULT 0 | 失败执行次数 |
| description | TEXT |  | 任务描述说明 |
| timeout | INTEGER |  | 任务超时时间，秒 |
| max_retries | INTEGER | DEFAULT 3 | 最大重试次数 |
| retry_delay | INTEGER | DEFAULT 60 | 重试延迟，秒 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(task_name)`
- `INDEX(enabled, next_run_at)`
- `INDEX(task_type, enabled)`
- `INDEX(schedule_type)`
- `INDEX(last_run_at DESC)`

**字段说明**：
- **schedule_type 调度类型**：
  - `cron`：使用cron表达式，schedule_config 示例：`{"cron": "0 */6 * * *", "timezone": "Asia/Shanghai"}`
  - `interval`：固定间隔执行，schedule_config 示例：`{"interval": 3600, "unit": "seconds"}`
  - `one_time`：一次性任务，schedule_config 示例：`{"run_at": "2024-01-01T00:00:00Z"}`
  - `manual`：手动触发，不自动执行

- **handler 处理器标识**：
  - 格式：`module.function` 或 `class.method`
  - 示例：`tasks.pt_sync.sync_all_sites`、`tasks.subscription.check_subscriptions`

- **handler_params 参数模板**：
  - 定义任务执行时的默认参数
  - 示例：`{"site_ids": [1, 2, 3], "sync_type": "incremental"}`
  - 实例执行时可被 task_queue.handler_params 覆盖

---

## 3. task_queue（任务队列）
**用途**：存储待执行和执行中的任务实例，支持重试和优先级调度

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| scheduled_task_id | INTEGER | FK → scheduled_tasks | 来源的调度任务ID，手动任务可为NULL |
| task_type | VARCHAR(50) | NOT NULL | 任务类型：与scheduled_tasks.task_type一致 |
| task_name | VARCHAR(255) | NOT NULL | 任务名称，可重复（同一任务多次执行） |
| related_type | VARCHAR(50) |  | 关联实体类型：pt_site/subscription/user等 |
| related_id | INTEGER |  | 关联实体ID，如site_id、subscription_id等 |
| status | VARCHAR(20) | DEFAULT 'pending' | 任务状态：pending/running/completed/failed/cancelled/timeout |
| priority | INTEGER | DEFAULT 0 | 任务优先级，数值越大优先级越高 |
| handler | VARCHAR(255) | NOT NULL | 处理器标识，对应后端处理函数路径 |
| handler_params | JSON |  | 处理器参数，JSON格式，优先级高于模板参数 |
| scheduled_at | TIMESTAMP |  | 计划执行时间 |
| started_at | TIMESTAMP |  | 实际开始执行时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 执行耗时，秒 |
| retry_count | INTEGER | DEFAULT 0 | 当前重试次数 |
| max_retries | INTEGER | DEFAULT 3 | 最大重试次数 |
| next_retry_at | TIMESTAMP |  | 下次重试时间 |
| worker_id | VARCHAR(100) |  | 执行该任务的工作进程ID |
| result | JSON |  | 执行结果，JSON格式 |
| error_message | TEXT |  | 错误信息 |
| error_detail | JSON |  | 详细错误信息，JSON格式 |
| progress | INTEGER | CHECK (progress BETWEEN 0 AND 100) | 任务进度 0-100 |
| progress_detail | JSON |  | 进度详情，JSON格式 |
| logs | TEXT |  | 任务执行日志 |
| metadata | JSON |  | 任务元数据，JSON格式 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `INDEX(status, priority DESC, scheduled_at)`
- `INDEX(task_type, status)`
- `INDEX(scheduled_task_id, created_at DESC)`
- `INDEX(related_type, related_id)`
- `INDEX(status, next_retry_at)`
- `INDEX(created_at DESC)`
- `INDEX(worker_id, status)`

**字段说明**：
- **status 任务状态**：
  - `pending`：等待执行
  - `running`：执行中
  - `completed`：执行成功
  - `failed`：执行失败（已达最大重试次数）
  - `cancelled`：已取消
  - `timeout`：执行超时

- **handler_params 参数优先级**：
  - 实例参数（task_queue.handler_params）优先级高于模板参数（scheduled_tasks.handler_params）
  - 执行时合并两者，实例参数覆盖同名模板参数
  - 示例场景：模板定义 `{"sync_type": "incremental"}`，实例覆盖为 `{"sync_type": "full", "force": true}`

- **related_type 和 related_id**：
  - 用于关联业务实体，便于查询某个实体相关的所有任务
  - 示例：`related_type="pt_site", related_id=1` 表示该任务关联 pt_sites 表 id=1 的站点
  - 示例：`related_type="subscription", related_id=5` 表示该任务关联 subscriptions 表 id=5 的订阅

- **重试逻辑**：
  - 任务失败后，如果 `retry_count < max_retries`，自动创建重试
  - `next_retry_at` 根据重试策略计算（指数退避或固定延迟）
  - 达到最大重试次数后，状态变更为 `failed`
