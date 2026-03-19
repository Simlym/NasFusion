# 日志系统表

## 1. sync_logs（同步日志）
**用途**：记录PT站点同步任务的详细日志

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| site_id | INTEGER | FK → pt_sites | 站点ID |
| sync_type | VARCHAR(20) | NOT NULL | 同步类型：full/incremental/manual |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 耗时，秒 |
| status | VARCHAR(20) | NOT NULL | 状态：running/success/failed/cancelled |
| total_pages | INTEGER |  | 总翻页数 |
| resources_found | INTEGER |  | 发现资源数 |
| resources_new | INTEGER |  | 新增资源数 |
| resources_updated | INTEGER |  | 更新资源数 |
| resources_skipped | INTEGER |  | 跳过资源数 |
| resources_error | INTEGER |  | 错误资源数 |
| sync_strategy | VARCHAR(20) |  | 同步策略：时间/页码/ID基准 |
| sync_params | JSON |  | 同步参数，JSON |
| error_message | TEXT |  | 错误信息 |
| error_detail | JSON |  | 详细错误，JSON |
| error_resources | JSON |  | 错误资源列表，JSON |
| requests_count | INTEGER |  | 请求次数 |
| avg_response_time | INTEGER |  | 平均响应时间，毫秒 |
| rate_limited | BOOLEAN |  | 是否触发限流 |
| peak_memory_usage | BIGINT |  | 峰值内存使用(字节) |
| cpu_usage_percent | DECIMAL(5,2) |  | CPU使用率 |
| network_bytes_received | BIGINT |  | 网络接收字节数 |
| duplicate_resources | INTEGER | DEFAULT 0 | 重复资源数 |
| invalid_resources | INTEGER | DEFAULT 0 | 无效资源数 |
| quality_distribution | JSON |  | 质量分布统计 |
| incremental_checkpoint | TEXT |  | 增量同步检查点 |
| pages_processed | INTEGER | DEFAULT 0 | 已处理页数 |
| items_per_page | INTEGER | DEFAULT 0 | 每页平均项目数 |
| response_times | JSON |  | 响应时间分布 |
| error_types | JSON |  | 错误类型统计 |
| auto_download_triggered | INTEGER | DEFAULT 0 | 触发的自动下载数 |
| recommendations_generated | INTEGER | DEFAULT 0 | 生成的推荐数 |
| debug_info | JSON |  | 调试信息 |
| sync_version | VARCHAR(20) |  | 同步引擎版本 |
| user_agent | TEXT |  | 使用的User-Agent |
| proxy_used | BOOLEAN | DEFAULT FALSE | 是否使用代理 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(site_id, started_at DESC)`
- `INDEX(status, started_at DESC)`

---

## 2. organize_logs（整理日志）
**用途**：记录媒体整理任务的详细日志

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| media_file_id | INTEGER | FK → media_files | 媒体文件ID |
| task_type | VARCHAR(20) | NOT NULL | 任务类型：identify/organize/scrape/all |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 耗时，秒 |
| status | VARCHAR(20) | NOT NULL | 状态：success/failed/cancelled |
| steps | JSON |  | 步骤记录，JSON数组 |
| error_step | VARCHAR(50) |  | 失败步骤 |
| error_message | TEXT |  | 错误信息 |
| error_detail | JSON |  | 详细错误，JSON |
| trigger_type | VARCHAR(20) |  | 触发类型：auto/manual/batch |
| triggered_by | VARCHAR(100) |  | 触发者，如download_complete |
| file_analysis | JSON |  | 文件分析结果 |
| identification_details | JSON |  | 识别详细信息 |
| organization_decision | JSON |  | 整理决策逻辑 |
| scraping_details | JSON |  | 刮削详细信息 |
| media_server_sync | JSON |  | 媒体服务器同步信息 |
| io_operations | JSON |  | IO操作统计 |
| batch_id | VARCHAR(50) |  | 批量操作ID |
| batch_total | INTEGER |  | 批量总数 |
| batch_progress | INTEGER | DEFAULT 0 | 批量进度 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(media_file_id, started_at DESC)`
- `INDEX(status, started_at DESC)`
- `INDEX(task_type, status)`

---

## 3. download_logs（下载日志/事件）
**用途**：记录下载任务的关键事件

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| download_task_id | INTEGER | FK → download_tasks | 下载任务ID |
| event_type | VARCHAR(20) | NOT NULL | 事件类型：created/started/paused/resumed/completed/error/deleted |
| message | TEXT |  | 事件描述 |
| data | JSON |  | 事件数据，JSON |
| error_code | VARCHAR(50) |  | 错误代码 |
| error_message | TEXT |  | 错误信息 |
| event_at | TIMESTAMP | NOT NULL | 事件时间 |
| progress_snapshot | JSON |  | 进度快照 |
| network_info | JSON |  | 网络状态信息 |
| seeding_info | JSON |  | 做种信息 |
| file_details | JSON |  | 文件详细信息 |
| client_info | JSON |  | 下载器客户端信息 |
| user_action | VARCHAR(50) |  | 用户操作类型 |
| user_trigger | JSON |  | 用户触发信息 |
| auto_action | JSON |  | 自动化操作记录 |
| alert_info | JSON |  | 告警信息 |
| related_tasks | JSON |  | 相关任务信息 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(download_task_id, event_at DESC)`
- `INDEX(event_type, event_at DESC)`

---

## 4. scan_tasks（扫描任务记录）
**用途**：记录目录扫描任务历史

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| scan_type | VARCHAR(20) | NOT NULL | 扫描类型：manual/scheduled/download_complete |
| scan_path | TEXT | NOT NULL | 扫描路径 |
| status | VARCHAR(20) | NOT NULL | 状态：running/completed/failed/cancelled |
| progress | INTEGER | CHECK (0-100) | 进度 0-100 |
| total_files | INTEGER |  | 总文件数 |
| new_files | INTEGER |  | 新增文件数 |
| updated_files | INTEGER |  | 更新文件数 |
| deleted_files | INTEGER |  | 删除文件数 |
| error_files | INTEGER |  | 错误文件数 |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 耗时，秒 |
| error_message | TEXT |  | 错误信息 |
| error_files_detail | JSON |  | 错误文件列表，JSON |
| scan_config | JSON |  | 扫描配置 |
| performance_metrics | JSON |  | 性能指标 |
| user_id | INTEGER | FK → users | 触发用户 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(status, started_at DESC)`
- `INDEX(scan_path)`
- `INDEX(scan_type)`
- `INDEX(user_id)`

---

## 5. notification_logs（通知日志）
**用途**：记录所有发送的通知

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| channel_id | INTEGER | FK → notification_channels | 通知渠道ID |
| event_type | VARCHAR(50) | NOT NULL | 事件类型 |
| title | VARCHAR(500) | NOT NULL | 通知标题 |
| message | TEXT | NOT NULL | 通知内容 |
| data | JSON |  | 关联数据，JSON |
| status | VARCHAR(20) | NOT NULL | 状态：pending/sent/failed |
| sent_at | TIMESTAMP |  | 发送时间 |
| error_message | TEXT |  | 错误信息 |
| retry_count | INTEGER | DEFAULT 0 | 重试次数 |
| severity | VARCHAR(20) | DEFAULT 'info' | 严重级别：info/success/warning/error/critical |
| priority | INTEGER | DEFAULT 5 | 消息优先级 |
| delivery_details | JSON |  | 发送详情 |
| read_at | TIMESTAMP |  | 阅读时间 |
| clicked_at | TIMESTAMP |  | 点击时间 |
| action_taken | VARCHAR(50) |  | 用户操作 |
| message_format | VARCHAR(20) | DEFAULT 'text' | 消息格式：text/html/markdown |
| rendered_content | TEXT |  | 渲染后的内容 |
| user_id | INTEGER | FK → users | 目标用户ID |
| session_id | VARCHAR(100) |  | 会话ID |
| test_group | VARCHAR(50) |  | 测试组 |
| template_version | VARCHAR(20) |  | 使用的模板版本 |
| variant | VARCHAR(20) |  | 消息变体 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(channel_id, created_at DESC)`
- `INDEX(status, created_at)`
- `INDEX(user_id, created_at DESC)`
- `INDEX(event_type, severity)`

---

## 6. ai_recommendation_logs（AI推荐日志）
**用途**：记录AI推荐的历史和成本

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| recommendation_type | VARCHAR(20) | NOT NULL | 推荐类型：daily/manual/triggered |
| user_profile | JSON |  | 用户画像摘要 |
| available_resources_count | INTEGER |  | 可选资源数量 |
| prompt_tokens | INTEGER |  | Prompt token数 |
| recommendations | JSON |  | 推荐结果，JSON数组 |
| recommendations_count | INTEGER |  | 推荐数量 |
| completion_tokens | INTEGER |  | 返回token数 |
| ai_provider | VARCHAR(20) |  | AI提供商：openai/claude/ollama |
| model_used | VARCHAR(50) |  | 使用的模型名称 |
| estimated_cost | DECIMAL(10,6) |  | 估算成本，USD |
| status | VARCHAR(20) | NOT NULL | 状态：success/failed |
| error_message | TEXT |  | 错误信息 |
| execution_time | INTEGER |  | 执行时长，秒 |
| user_id | INTEGER | FK → users | 用户ID |
| feedback_score | INTEGER | CHECK (1-10) | 用户反馈评分 |
| feedback_received_at | TIMESTAMP |  | 反馈接收时间 |
| click_through_rate | DECIMAL(5,4) |  | 点击率 |
| conversion_count | INTEGER |  | 转化数（下载等） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP |  | 完成时间 |

**索引设计**：
- `INDEX(recommendation_type, created_at DESC)`
- `INDEX(ai_provider, created_at DESC)`
- `INDEX(status)`
- `INDEX(user_id, created_at DESC)`
- `INDEX(model_used, created_at DESC)`
