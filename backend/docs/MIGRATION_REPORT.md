# 任务处理器 Handler 字段迁移报告

## 问题描述

在将任务处理器架构重构为注册表模式后,发现旧的 handler 字段格式与新架构不兼容:

**旧格式示例**:
- `tasks.pt_sync.sync_site` (点号路径格式)
- `app.services.subscription_check_handler.SubscriptionCheckHandler.check_all_subscriptions` (完整类路径)
- `sync_all_download_status` (函数名)
- `cleanup_task_executions` (函数名)

**新格式**:
- `pt_resource_sync` (任务类型常量,与 task_type 一致)
- `subscription_check`
- `download_status_sync`
- `task_execution_cleanup`

## 迁移内容

### 1. 数据库数据迁移

**脚本**: `backend/migrate_handlers.py`

迁移了 4 个现有调度任务的 handler 字段:

| ID | 任务名称 | 旧 Handler | 新 Handler |
|----|---------|-----------|-----------|
| 1 | mteam站点同步 | `tasks.pt_sync.sync_site` | `pt_resource_sync` |
| 2 | 订阅自动检查(全局) | `app.services.subscription_check_handler...` | `subscription_check` |
| 3 | 监听下载完成 | `sync_all_download_status` | `download_status_sync` |
| 4 | 清理任务执行历史 | `cleanup_task_executions` | `task_execution_cleanup` |

**执行结果**: ✅ 成功迁移 4 个任务

### 2. 代码修复

修复了以下文件中硬编码的 handler 值:

#### 2.1 调度任务创建
- ✅ `app/services/scheduled_task_service.py` - PT同步任务创建
- ✅ `app/core/init_system.py` - 系统初始化任务(3处)
- ✅ `scripts/init/init_download_sync_task.py` - 下载同步任务初始化

#### 2.2 任务执行记录创建
- ✅ `app/api/v1/media_files.py` - 媒体文件扫描
- ✅ `app/api/v1/download_tasks.py` - 下载任务创建
- ✅ `app/api/v1/resource_identification.py` - 资源识别

**修复方式**: 将硬编码字符串改为使用 `TASK_TYPE_*` 常量

**示例**:
```python
# ❌ 旧代码
handler="tasks.pt_sync.sync_site"

# ✅ 新代码
handler=TASK_TYPE_PT_RESOURCE_SYNC
```

## 测试验证

### 1. 注册表测试

**测试脚本**: `backend/test_task_execution.py`

**结果**:
```
已注册的任务处理器数量: 7

任务类型 -> 处理器类映射:
[OK] pt_resource_sync               -> PTResourceSyncHandler
[OK] pt_resource_identify           -> PTResourceIdentifyHandler
[OK] subscription_check             -> SubscriptionCheckHandler
[OK] media_file_scan                -> MediaFileScanHandler
[OK] download_create                -> DownloadCreateHandler
[OK] download_status_sync           -> DownloadStatusSyncHandler
[OK] task_execution_cleanup         -> TaskExecutionCleanupHandler

[SUCCESS] 所有任务类型都已正确注册
```

### 2. 数据库验证

**验证脚本**: `backend/check_handlers.py`

**结果**: ✅ 所有调度任务的 handler 字段均为新格式(与 task_type 一致)

## 设计规范

### Handler 字段规范

从此次迁移开始,所有 `handler` 字段遵循以下规范:

1. **ScheduledTask**: `handler` = `task_type`(均使用 `TASK_TYPE_*` 常量)
2. **TaskExecution**: `handler` = `task_type`(均使用 `TASK_TYPE_*` 常量)
3. **处理器查找**: 通过 `TaskHandlerRegistry.get_handler(task_type)` 获取处理器类

### 添加新任务类型的步骤

1. 在 `app/constants/task.py` 定义 `TASK_TYPE_*` 常量
2. 创建处理器类(继承 `BaseTaskHandler`)
3. 在 `app/tasks/registry.py` 注册处理器
4. 创建任务时使用 `handler=TASK_TYPE_*`

## 文件清单

### 新增文件
- `backend/migrate_handlers.py` - 数据库迁移脚本
- `backend/check_handlers.py` - Handler 字段验证脚本
- `backend/test_task_execution.py` - 任务执行系统测试脚本
- `backend/MIGRATION_REPORT.md` - 本迁移报告

### 修改文件
- `app/services/scheduled_task_service.py`
- `app/core/init_system.py`
- `app/api/v1/media_files.py`
- `app/api/v1/download_tasks.py`
- `app/api/v1/resource_identification.py`
- `scripts/init/init_download_sync_task.py`

## 影响范围

- ✅ **调度任务**: 所有现有和新建的调度任务
- ✅ **任务执行**: 所有通过 API 触发的任务执行
- ✅ **向前兼容**: 旧 handler 格式已全部迁移,无兼容性问题

## 后续建议

1. ✅ **代码审查**: 确保所有 `handler=` 赋值都使用常量而非字符串
2. ✅ **文档更新**: 在 `CLAUDE.md` 中添加 handler 字段规范说明
3. ⚠️ **监控运行**: 观察任务执行是否正常,特别是定时任务

## 迁移完成时间

- **开始**: 2025-12-07
- **完成**: 2025-12-07
- **状态**: ✅ 已完成
- **测试**: ✅ 全部通过

---

**维护者**: Claude Code
**更新日期**: 2025-12-07
