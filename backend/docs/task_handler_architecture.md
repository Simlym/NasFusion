# 任务处理器架构说明文档

**版本**: v1.0
**创建日期**: 2025-12-05
**维护者**: NasFusion Team

---

## 目录

1. [概述](#概述)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [工作流程](#工作流程)
5. [已实现的任务处理器](#已实现的任务处理器)
6. [如何添加新任务类型](#如何添加新任务类型)
7. [最佳实践](#最佳实践)
8. [故障排查](#故障排查)

---

## 概述

### 背景

NasFusion 的任务调度系统基于 APScheduler，负责执行各种后台任务（PT 站点同步、媒体扫描、订阅检查等）。在 v2.2 重构之前，所有任务处理逻辑都集中在 `scheduler_manager.py` 的一个巨大方法中（673 行），导致：

- ❌ 代码难以维护（单个方法过长）
- ❌ 添加新任务类型需要修改核心代码
- ❌ 测试困难（逻辑高度耦合）
- ❌ 代码重复（类似的进度更新和日志记录逻辑）

### 解决方案

引入**任务处理器架构（Task Handler Architecture）**，使用注册表模式（Registry Pattern）将任务处理逻辑模块化：

- ✅ 每种任务类型有独立的处理器文件
- ✅ 统一的处理器接口（`BaseTaskHandler`）
- ✅ 动态注册机制（`TaskHandlerRegistry`）
- ✅ 调度器核心代码简化为 12 行

### 重构效果

| 指标 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| `scheduler_manager.py` | 1154 行 | 495 行 | **-57%** |
| `_run_task_handler` 方法 | 673 行 | 12 行 | **-98%** |
| 文件数量 | 2 个 | 12 个 | 模块化 |
| 可维护性 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 大幅提升 |

---

## 架构设计

### 目录结构

```
backend/app/tasks/
├── __init__.py                          # 导出公共接口
├── base.py                              # BaseTaskHandler 抽象基类
├── registry.py                          # TaskHandlerRegistry 注册表
└── handlers/                            # 任务处理器实现
    ├── __init__.py                      # 导出所有处理器
    ├── pt_sync_handler.py               # PT站点同步
    ├── batch_identify_handler.py        # 批量识别
    ├── subscription_check_handler.py    # 订阅检查
    ├── scan_media_handler.py            # 媒体扫描
    ├── create_download_handler.py       # 创建下载
    ├── sync_download_handler.py         # 同步下载状态
    └── cleanup_handler.py               # 清理任务
```

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                  Scheduler Manager                      │
│  (scheduler_manager.py)                                 │
│  ┌───────────────────────────────────────────────────┐ │
│  │  async def start():                               │ │
│  │      register_all_handlers()  # 注册所有处理器    │ │
│  │      _load_scheduled_tasks()                      │ │
│  │      _scheduler.start()                           │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │  async def _run_task_handler(task):               │ │
│  │      handler = Registry.get_handler(task.type)    │ │
│  │      return await handler.execute(db, params, id) │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Task Handler Registry                      │
│  (tasks/registry.py)                                    │
│  ┌───────────────────────────────────────────────────┐ │
│  │  _handlers = {                                    │ │
│  │      "pt_sync": PTSyncHandler,                    │ │
│  │      "batch_identify": BatchIdentifyHandler,      │ │
│  │      "subscription_check": SubscriptionCheck...   │ │
│  │      ...                                          │ │
│  │  }                                                │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Task Handlers                          │
│  (tasks/handlers/)                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ PTSync       │  │ BatchIdentify│  │ Subscription │ │
│  │ Handler      │  │ Handler      │  │ CheckHandler │ │
│  │              │  │              │  │              │ │
│  │ execute()    │  │ execute()    │  │ execute()    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ ScanMedia    │  │ CreateDown   │  │ Cleanup      │ │
│  │ Handler      │  │ loadHandler  │  │ Handler      │ │
│  │              │  │              │  │              │ │
│  │ execute()    │  │ execute()    │  │ execute()    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. 基类：`BaseTaskHandler`

**文件位置**: `backend/app/tasks/base.py`

**作用**: 定义所有任务处理器的统一接口。

**完整代码**:
```python
# -*- coding: utf-8 -*-
"""
任务处理器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession


class BaseTaskHandler(ABC):
    """任务处理器基类"""

    @staticmethod
    @abstractmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行任务

        Args:
            db: 数据库会话
            params: 处理器参数 (来自 task.handler_params)
            execution_id: 任务执行记录ID (用于进度更新/日志)

        Returns:
            执行结果字典
        """
        pass
```

**设计要点**:
- 使用 ABC（抽象基类）确保所有子类实现 `execute` 方法
- `@staticmethod` 装饰器表示无需实例化即可调用
- 统一的方法签名：`(db, params, execution_id) -> Dict`

---

### 2. 注册表：`TaskHandlerRegistry`

**文件位置**: `backend/app/tasks/registry.py`

**作用**: 管理任务类型与处理器的映射关系。

**完整代码**:
```python
# -*- coding: utf-8 -*-
"""
任务处理器注册表
"""
import logging
from typing import Dict, Type, Optional

from app.tasks.base import BaseTaskHandler

logger = logging.getLogger(__name__)


class TaskHandlerRegistry:
    """任务处理器注册表"""

    _handlers: Dict[str, Type[BaseTaskHandler]] = {}

    @classmethod
    def register(cls, task_type: str, handler_class: Type[BaseTaskHandler]):
        """注册处理器"""
        cls._handlers[task_type] = handler_class
        logger.debug(f"已注册任务处理器: {task_type} -> {handler_class.__name__}")

    @classmethod
    def get_handler(cls, task_type: str) -> Optional[Type[BaseTaskHandler]]:
        """获取处理器"""
        return cls._handlers.get(task_type)

    @classmethod
    def get_all_handlers(cls) -> Dict[str, Type[BaseTaskHandler]]:
        """获取所有已注册的处理器"""
        return cls._handlers.copy()


def register_all_handlers():
    """注册所有任务处理器"""
    from app.constants import (
        TASK_TYPE_PT_SYNC,
        TASK_TYPE_BATCH_IDENTIFY,
        TASK_TYPE_SUBSCRIPTION_CHECK,
        TASK_TYPE_SCAN_MEDIA,
        TASK_TYPE_CREATE_DOWNLOAD,
        TASK_TYPE_SYNC_DOWNLOAD_STATUS,
        TASK_TYPE_CLEANUP,
    )
    from app.tasks.handlers import (
        PTSyncHandler,
        BatchIdentifyHandler,
        SubscriptionCheckHandler,
        ScanMediaHandler,
        CreateDownloadHandler,
        SyncDownloadHandler,
        CleanupHandler,
    )

    TaskHandlerRegistry.register(TASK_TYPE_PT_SYNC, PTSyncHandler)
    TaskHandlerRegistry.register(TASK_TYPE_BATCH_IDENTIFY, BatchIdentifyHandler)
    TaskHandlerRegistry.register(TASK_TYPE_SUBSCRIPTION_CHECK, SubscriptionCheckHandler)
    TaskHandlerRegistry.register(TASK_TYPE_SCAN_MEDIA, ScanMediaHandler)
    TaskHandlerRegistry.register(TASK_TYPE_CREATE_DOWNLOAD, CreateDownloadHandler)
    TaskHandlerRegistry.register(TASK_TYPE_SYNC_DOWNLOAD_STATUS, SyncDownloadHandler)
    TaskHandlerRegistry.register(TASK_TYPE_CLEANUP, CleanupHandler)

    logger.info(f"已注册 {len(TaskHandlerRegistry.get_all_handlers())} 个任务处理器")
```

**设计要点**:
- 使用类变量 `_handlers` 存储映射关系
- `@classmethod` 允许直接通过类调用，无需实例化
- `register_all_handlers()` 统一注册，在调度器启动时调用

---

### 3. 调度器集成

**文件位置**: `backend/app/services/scheduler_manager.py`

**核心改动**:

**启动时注册处理器**:
```python
async def start(self):
    """启动调度器"""
    if self._scheduler.running:
        logger.warning("调度器已在运行中")
        return

    # 注册所有任务处理器 (新增)
    from app.tasks.registry import register_all_handlers
    register_all_handlers()

    # 加载所有已启用的任务
    await self._load_scheduled_tasks()

    # 启动调度器
    self._scheduler.start()
    logger.info("任务调度器已启动")
```

**简化后的任务执行方法**:
```python
async def _run_task_handler(
    self, db: AsyncSession, task: ScheduledTask, execution
) -> Dict[str, Any]:
    """运行任务处理器"""
    from app.tasks.registry import TaskHandlerRegistry

    handler_class = TaskHandlerRegistry.get_handler(task.task_type)
    if not handler_class:
        raise NotImplementedError(f"任务类型 {task.task_type} 暂不支持")

    params = task.handler_params or {}
    return await handler_class.execute(db, params, execution.id)
```

**重构前对比**:
```python
# 重构前：673 行的巨大 if/elif 链
async def _run_task_handler_old(self, db, task, execution):
    params = task.handler_params or {}

    if task.task_type == TASK_TYPE_PT_SYNC:
        # 35 行代码...
    elif task.task_type == TASK_TYPE_BATCH_IDENTIFY:
        # 50 行代码...
    elif task.task_type == TASK_TYPE_SUBSCRIPTION_CHECK:
        # 118 行代码...
    # ... 更多分支
```

---

## 工作流程

### 1. 系统启动流程

```
应用启动 (main.py)
    ↓
启动调度器 (scheduler_manager.start())
    ↓
注册所有处理器 (register_all_handlers())
    ├─ TaskHandlerRegistry.register(TASK_TYPE_PT_SYNC, PTSyncHandler)
    ├─ TaskHandlerRegistry.register(TASK_TYPE_BATCH_IDENTIFY, BatchIdentifyHandler)
    └─ ...
    ↓
加载已启用的定时任务 (_load_scheduled_tasks())
    ↓
APScheduler 开始运行
```

### 2. 定时任务执行流程

```
定时任务触发 (APScheduler)
    ↓
_execute_scheduled_task(task_id)
    ├─ 创建 TaskExecution 记录
    ├─ 更新任务状态为 RUNNING
    └─ 调用 _run_task_handler(task, execution)
        ↓
        获取处理器 (TaskHandlerRegistry.get_handler(task.task_type))
        ↓
        执行处理器 (handler.execute(db, params, execution_id))
            ├─ 更新日志 (TaskExecutionService.append_log)
            ├─ 更新进度 (TaskExecutionService.update_progress)
            └─ 返回结果 (Dict[str, Any])
        ↓
        更新任务状态为 SUCCESS/FAILED
        ↓
        发布完成/失败事件 (event_bus.publish)
```

### 3. 手动触发任务流程

```
API 请求 (POST /api/v1/scheduled-tasks/{id}/run)
    ↓
scheduler_manager.run_task_now(task_id)
    ├─ 创建 TaskExecution 记录
    └─ asyncio.create_task(_execute_task_by_execution(execution.id))
        ↓
        后台执行任务 (不阻塞 API 响应)
        ↓
        同样调用 _run_task_handler() → handler.execute()
        ↓
        前端轮询 /api/v1/task-executions/{id} 获取进度
```

---

## 已实现的任务处理器

### 1. PT 站点同步 (`PTSyncHandler`)

**文件**: `tasks/handlers/pt_sync_handler.py`
**任务类型**: `TASK_TYPE_PT_SYNC` (`"pt_sync"`)

**功能**: 从 PT 站点同步资源到本地数据库

**参数**:
```python
{
    "site_id": 1,                    # 站点 ID (必需)
    "sync_type": "incremental",      # 同步类型: incremental/full
    "max_pages": 10,                 # 最大页数 (可选)
    "start_page": 1                  # 起始页 (可选)
}
```

**返回结果**:
```python
{
    "sync_log_id": 123,
    "resources_found": 500,
    "resources_new": 50,
    "resources_updated": 10,
    "pages_processed": 10
}
```

---

### 2. 批量识别 (`BatchIdentifyHandler`)

**文件**: `tasks/handlers/batch_identify_handler.py`
**任务类型**: `TASK_TYPE_BATCH_IDENTIFY` (`"batch_identify"`)

**功能**: 批量识别 PT 资源并关联到 TMDB/豆瓣

**参数**:
```python
{
    "pt_resource_ids": [1, 2, 3],    # PT 资源 ID 列表 (必需)
    "media_type": "auto",            # 媒体类型: auto/movie/tv
    "skip_errors": True              # 是否跳过错误
}
```

**返回结果**:
```python
{
    "total": 3,
    "success": 2,
    "failed": 1,
    "skipped": 0,
    "error_count": 1
}
```

**特点**: 支持步骤式进度更新

---

### 3. 订阅检查 (`SubscriptionCheckHandler`)

**文件**: `tasks/handlers/subscription_check_handler.py`
**任务类型**: `TASK_TYPE_SUBSCRIPTION_CHECK` (`"subscription_check"`)

**功能**: 检查订阅并自动下载匹配的资源

**参数**:
```python
{
    "check_all": True,               # 检查所有活跃订阅
    "subscription_ids": [1, 2],      # 指定订阅 ID 列表
    "subscription_id": 1             # 单个订阅 ID (向后兼容)
}
```

**返回结果**:
```python
{
    "total": 10,
    "checked": 9,
    "matched": 3,
    "downloaded": 2,
    "errors": 1
}
```

**特点**:
- 支持单个/批量/全部订阅检查
- 自动触发下载和通知
- 记录订阅检查日志

---

### 4. 媒体扫描 (`ScanMediaHandler`)

**文件**: `tasks/handlers/scan_media_handler.py`
**任务类型**: `TASK_TYPE_SCAN_MEDIA` (`"scan_media"`)

**功能**: 扫描目录并创建媒体文件记录

**参数**:
```python
{
    "directory": "./data/downloads",  # 目录路径 (必需)
    "recursive": True,                # 是否递归扫描
    "media_type": "movie"             # 媒体类型过滤 (可选)
}
```

**返回结果**:
```python
{
    "directory": "./data/downloads",
    "files_created": 150,
    "file_ids": [1, 2, 3, ...]
}
```

---

### 5. 创建下载 (`CreateDownloadHandler`)

**文件**: `tasks/handlers/create_download_handler.py`
**任务类型**: `TASK_TYPE_CREATE_DOWNLOAD` (`"create_download"`)

**功能**: 下载种子文件并推送到下载器

**参数**:
```python
{
    "pt_resource_id": 1,              # PT 资源 ID (必需)
    "downloader_config_id": 1,        # 下载器配置 ID (必需)
    "save_path": "/downloads/movies", # 保存路径 (必需)
    "auto_organize": True,            # 自动整理
    "keep_seeding": True,             # 保持做种
    "seeding_time_limit": 72,         # 做种时间限制 (小时)
    "seeding_ratio_limit": 2.0,       # 分享率限制
    "user_id": 1                      # 用户 ID
}
```

**返回结果**:
```python
{
    "download_task_id": 123,
    "task_hash": "abc123...",
    "torrent_name": "电影名称.mkv",
    "existed": False
}
```

**特点**:
- 5 个步骤的详细进度跟踪
- 自动处理 HR 限制
- 检查重复下载

---

### 6. 同步下载状态 (`SyncDownloadHandler`)

**文件**: `tasks/handlers/sync_download_handler.py`
**任务类型**: `TASK_TYPE_SYNC_DOWNLOAD_STATUS` (`"sync_download_status"`)

**功能**: 同步下载器中的任务状态

**参数**: 无

**返回结果**:
```python
{
    "total_tasks": 20,
    "completed_count": 3,
    "error_count": 1
}
```

---

### 7. 清理任务 (`CleanupHandler`)

**文件**: `tasks/handlers/cleanup_handler.py`
**任务类型**: `TASK_TYPE_CLEANUP` (`"cleanup"`)

**功能**: 清理过期的任务执行记录

**参数**:
```python
{
    "days": 7,                        # 清理多少天前的记录
    "keep_failed": True               # 是否保留失败记录
}
```

**返回结果**:
```python
{
    "deleted_count": 150,
    "cutoff_date": "2025-11-28T00:00:00+08:00",
    "keep_failed": True
}
```

---

## 如何添加新任务类型

### 完整示例：添加"邮件通知"任务

假设我们要添加一个每天发送统计报告邮件的任务。

#### 步骤 1：定义任务类型常量

**文件**: `backend/app/constants/task.py`

```python
# 在文件末尾添加
TASK_TYPE_SEND_EMAIL_REPORT = "send_email_report"

# 更新显示名称映射
TASK_TYPE_DISPLAY_NAMES = {
    # ... 现有映射
    TASK_TYPE_SEND_EMAIL_REPORT: "发送邮件报告",
}
```

#### 步骤 2：创建任务处理器

**文件**: `backend/app/tasks/handlers/send_email_report_handler.py`

```python
# -*- coding: utf-8 -*-
"""
邮件报告任务处理器
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.task_execution_service import TaskExecutionService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class SendEmailReportHandler(BaseTaskHandler):
    """发送邮件报告任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行邮件报告发送

        Args:
            db: 数据库会话
            params: 处理器参数
                - recipients: 收件人列表 (必需)
                - report_type: 报告类型 (daily/weekly/monthly)
            execution_id: 任务执行ID

        Returns:
            发送结果
        """
        recipients = params.get("recipients", [])
        if not recipients:
            raise ValueError("邮件报告任务缺少recipients参数")

        report_type = params.get("report_type", "daily")

        await TaskExecutionService.append_log(
            db, execution_id, f"开始生成{report_type}报告，收件人: {len(recipients)}人"
        )

        # 步骤 1: 收集统计数据
        await TaskExecutionService.update_progress(db, execution_id, 20)
        stats = await _collect_statistics(db, report_type)

        await TaskExecutionService.append_log(
            db, execution_id, f"统计数据收集完成: {stats['total_downloads']}个下载任务"
        )

        # 步骤 2: 生成报告内容
        await TaskExecutionService.update_progress(db, execution_id, 50)
        report_html = await _generate_report_html(stats, report_type)

        await TaskExecutionService.append_log(
            db, execution_id, "报告内容生成完成"
        )

        # 步骤 3: 发送邮件
        await TaskExecutionService.update_progress(db, execution_id, 80)
        sent_count = 0
        failed_count = 0

        for recipient in recipients:
            try:
                await _send_email(recipient, report_html, report_type)
                sent_count += 1
                await TaskExecutionService.append_log(
                    db, execution_id, f"✓ 已发送到: {recipient}"
                )
            except Exception as e:
                failed_count += 1
                await TaskExecutionService.append_log(
                    db, execution_id, f"✗ 发送失败: {recipient}, 错误: {str(e)}"
                )

        # 完成
        await TaskExecutionService.update_progress(db, execution_id, 100)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"邮件发送完成: 成功{sent_count}个, 失败{failed_count}个"
        )

        return {
            "report_type": report_type,
            "total_recipients": len(recipients),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "statistics": stats,
        }


async def _collect_statistics(db: AsyncSession, report_type: str) -> Dict:
    """收集统计数据（示例）"""
    # 实现统计逻辑
    return {
        "total_downloads": 100,
        "completed_downloads": 80,
        "active_subscriptions": 20,
    }


async def _generate_report_html(stats: Dict, report_type: str) -> str:
    """生成 HTML 报告（示例）"""
    return f"""
    <html>
        <body>
            <h1>{report_type} 统计报告</h1>
            <p>总下载任务: {stats['total_downloads']}</p>
            <p>已完成: {stats['completed_downloads']}</p>
            <p>活跃订阅: {stats['active_subscriptions']}</p>
        </body>
    </html>
    """


async def _send_email(recipient: str, html: str, subject: str):
    """发送邮件（示例）"""
    # 实现邮件发送逻辑
    logger.info(f"发送邮件到 {recipient}")
```

#### 步骤 3：在 `handlers/__init__.py` 导出

**文件**: `backend/app/tasks/handlers/__init__.py`

```python
# 添加导入
from app.tasks.handlers.send_email_report_handler import SendEmailReportHandler

# 添加到 __all__
__all__ = [
    "PTSyncHandler",
    "BatchIdentifyHandler",
    "SubscriptionCheckHandler",
    "ScanMediaHandler",
    "CreateDownloadHandler",
    "SyncDownloadHandler",
    "CleanupHandler",
    "SendEmailReportHandler",  # 新增
]
```

#### 步骤 4：注册到注册表

**文件**: `backend/app/tasks/registry.py`

```python
def register_all_handlers():
    """注册所有任务处理器"""
    from app.constants import (
        # ... 现有常量
        TASK_TYPE_SEND_EMAIL_REPORT,  # 新增
    )
    from app.tasks.handlers import (
        # ... 现有处理器
        SendEmailReportHandler,  # 新增
    )

    # ... 现有注册
    TaskHandlerRegistry.register(TASK_TYPE_SEND_EMAIL_REPORT, SendEmailReportHandler)  # 新增

    logger.info(f"已注册 {len(TaskHandlerRegistry.get_all_handlers())} 个任务处理器")
```

#### 步骤 5：创建 API 接口（可选）

**文件**: `backend/app/api/v1/email_reports.py`

```python
from fastapi import APIRouter, Depends
from app.services.scheduler_manager import scheduler_manager
from app.schemas.task_execution import TaskExecutionCreate
from app.constants import TASK_TYPE_SEND_EMAIL_REPORT

router = APIRouter(prefix="/email-reports", tags=["邮件报告"])


@router.post("/send")
async def send_email_report(
    recipients: List[str],
    report_type: str = "daily"
):
    """手动触发邮件报告"""
    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_SEND_EMAIL_REPORT,
        task_name=f"发送{report_type}报告",
        handler="send_email_report",
        handler_params={
            "recipients": recipients,
            "report_type": report_type
        }
    )

    # 创建并执行任务
    execution_id = await scheduler_manager.run_task_now(execution_data)

    return {"execution_id": execution_id}
```

#### 步骤 6：创建定时任务（可选）

通过 API 或数据库直接插入：

```python
task_data = ScheduledTaskCreate(
    task_name="每日邮件报告",
    task_type=TASK_TYPE_SEND_EMAIL_REPORT,
    enabled=True,
    schedule_type=SCHEDULE_TYPE_CRON,
    schedule_config={"cron": "0 9 * * *", "timezone": "Asia/Shanghai"},  # 每天早上9点
    handler="send_email_report",
    handler_params={
        "recipients": ["admin@example.com"],
        "report_type": "daily"
    },
    description="每日统计报告邮件"
)
```

#### 步骤 7：重启应用测试

```bash
cd backend
python -m app.main
```

查看日志确认注册成功：
```
INFO: 已注册任务处理器: send_email_report -> SendEmailReportHandler
INFO: 已注册 8 个任务处理器
```

---

## 最佳实践

### 1. 进度更新策略

**推荐做法**:
```python
# 将任务分成若干步骤，每步更新进度
async def execute(db, params, execution_id):
    # 步骤 1: 验证 (0-20%)
    await TaskExecutionService.update_progress(db, execution_id, 0)
    validate_params(params)
    await TaskExecutionService.update_progress(db, execution_id, 20)

    # 步骤 2: 处理 (20-80%)
    await TaskExecutionService.append_log(db, execution_id, "开始处理")
    result = await process_data(db, params)
    await TaskExecutionService.update_progress(db, execution_id, 80)

    # 步骤 3: 完成 (80-100%)
    await save_result(db, result)
    await TaskExecutionService.update_progress(db, execution_id, 100)

    return result
```

**避免的做法**:
```python
# ❌ 不推荐：只在开始和结束更新进度
async def execute(db, params, execution_id):
    await TaskExecutionService.update_progress(db, execution_id, 0)
    # ... 长时间处理，用户看不到进度
    result = await long_running_task()
    await TaskExecutionService.update_progress(db, execution_id, 100)
    return result
```

### 2. 日志记录策略

**推荐做法**:
```python
# 记录关键步骤和结果
await TaskExecutionService.append_log(db, execution_id, "开始同步站点 MTeam")
await TaskExecutionService.append_log(db, execution_id, f"找到 {count} 个新资源")
await TaskExecutionService.append_log(db, execution_id, "同步完成")
```

**避免的做法**:
```python
# ❌ 不推荐：过度记录或不记录
# 过度记录会产生大量日志
for i in range(10000):
    await TaskExecutionService.append_log(db, execution_id, f"处理第{i}个")
```

### 3. 错误处理策略

**推荐做法**:
```python
async def execute(db, params, execution_id):
    try:
        # 主要逻辑
        result = await main_logic(db, params)
        return result
    except ValueError as e:
        # 参数错误，记录并重新抛出
        await TaskExecutionService.append_log(
            db, execution_id, f"参数错误: {str(e)}"
        )
        raise
    except Exception as e:
        # 未预期错误，记录详细信息
        logger.exception(f"任务执行失败: {e}")
        await TaskExecutionService.append_log(
            db, execution_id, f"执行失败: {str(e)}"
        )
        raise
```

### 4. 参数验证

**推荐做法**:
```python
async def execute(db, params, execution_id):
    # 早期验证所有必需参数
    required_params = ["site_id", "sync_type"]
    for param in required_params:
        if param not in params:
            raise ValueError(f"缺少必需参数: {param}")

    # 验证参数类型和范围
    site_id = params.get("site_id")
    if not isinstance(site_id, int) or site_id <= 0:
        raise ValueError(f"无效的 site_id: {site_id}")

    # 继续执行...
```

### 5. 返回值规范

**推荐做法**:
```python
# 返回清晰、有意义的结果字典
return {
    "sync_log_id": sync_log.id,       # 相关记录 ID
    "resources_new": 50,               # 统计数字
    "resources_updated": 10,
    "pages_processed": 5,
    "execution_time": 120,             # 执行时间（秒）
}
```

**避免的做法**:
```python
# ❌ 不推荐：返回不清晰的结果
return {"success": True}  # 缺少详细信息
return sync_log  # 返回模型对象（无法序列化）
```

---

## 故障排查

### 问题 1：任务未执行

**症状**: 定时任务到时间了但没有执行

**排查步骤**:
1. 检查任务是否启用：`SELECT * FROM scheduled_tasks WHERE enabled = true`
2. 检查调度器是否运行：查看日志中是否有 "任务调度器已启动"
3. 检查任务类型是否注册：查看日志中 "已注册 X 个任务处理器"
4. 检查任务时间配置：`next_run_at` 是否设置正确

**解决方案**:
```sql
-- 重新计算下次执行时间
UPDATE scheduled_tasks SET next_run_at = NOW() WHERE id = 1;
```

### 问题 2：处理器未注册

**症状**: 执行任务时报错 "任务类型 xxx 暂不支持"

**排查步骤**:
1. 检查 `TaskHandlerRegistry.get_handler(task_type)` 返回值
2. 检查 `register_all_handlers()` 是否被调用
3. 检查处理器是否在 `handlers/__init__.py` 中导出

**解决方案**:
```python
# 在 Python 控制台测试
from app.tasks.registry import TaskHandlerRegistry
print(TaskHandlerRegistry.get_all_handlers())
# 输出应该包含所有处理器
```

### 问题 3：进度不更新

**症状**: 前端轮询任务执行记录，但进度一直是 0

**排查步骤**:
1. 检查处理器中是否调用了 `update_progress()`
2. 检查数据库事务是否提交：`await db.commit()`
3. 检查 `execution_id` 是否正确传递

**解决方案**:
```python
# 确保调用 update_progress
await TaskExecutionService.update_progress(db, execution_id, 50)
# TaskExecutionService 内部会自动 commit
```

### 问题 4：任务执行超时

**症状**: 任务执行很长时间后被强制终止

**排查步骤**:
1. 检查任务的 `timeout` 配置
2. 检查是否有长时间阻塞的操作
3. 检查是否使用了 `async/await`

**解决方案**:
```python
# 增加超时时间
task.timeout = 3600  # 1小时

# 使用异步操作避免阻塞
# ❌ 错误：同步阻塞
time.sleep(10)

# ✅ 正确：异步等待
await asyncio.sleep(10)
```

### 问题 5：重复执行

**症状**: 同一个任务被执行了多次

**排查步骤**:
1. 检查是否有多个调度器实例
2. 检查任务的 `last_run_status` 是否卡在 `RUNNING`
3. 检查 APScheduler 的 `misfire_grace_time` 配置

**解决方案**:
```python
# 确保只有一个调度器实例（使用单例模式）
class SchedulerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# 重置卡住的任务状态
UPDATE scheduled_tasks
SET last_run_status = NULL, last_run_at = NULL
WHERE last_run_status = 'running';
```

---

## 附录

### A. 完整的处理器模板

```python
# -*- coding: utf-8 -*-
"""
[任务名称]任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class MyTaskHandler(BaseTaskHandler):
    """[任务描述]"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行[任务名称]

        Args:
            db: 数据库会话
            params: 处理器参数
                - param1: 参数1说明 (必需/可选)
                - param2: 参数2说明 (必需/可选)
            execution_id: 任务执行ID

        Returns:
            执行结果
        """
        # 1. 参数验证
        param1 = params.get("param1")
        if not param1:
            raise ValueError("缺少必需参数: param1")

        # 2. 记录开始
        await TaskExecutionService.append_log(
            db, execution_id, f"开始执行任务，参数: {param1}"
        )
        await TaskExecutionService.update_progress(db, execution_id, 0)

        # 3. 执行主要逻辑
        try:
            result = await _do_main_work(db, params)

            await TaskExecutionService.update_progress(db, execution_id, 50)

            # 后续处理
            final_result = await _finalize(db, result)

            await TaskExecutionService.update_progress(db, execution_id, 100)

        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}", exc_info=True)
            await TaskExecutionService.append_log(
                db, execution_id, f"执行失败: {str(e)}"
            )
            raise

        # 4. 返回结果
        await TaskExecutionService.append_log(
            db, execution_id, "任务执行完成"
        )

        return {
            "status": "success",
            "result": final_result,
        }


async def _do_main_work(db: AsyncSession, params: Dict) -> Any:
    """执行主要工作"""
    # 实现逻辑
    pass


async def _finalize(db: AsyncSession, result: Any) -> Dict:
    """完成处理"""
    # 实现逻辑
    return {"data": result}
```

### B. 相关文件清单

| 文件路径 | 说明 |
|----------|------|
| `backend/app/tasks/base.py` | 基类定义 |
| `backend/app/tasks/registry.py` | 注册表实现 |
| `backend/app/tasks/__init__.py` | 模块导出 |
| `backend/app/tasks/handlers/__init__.py` | 处理器导出 |
| `backend/app/tasks/handlers/*.py` | 各个处理器实现 |
| `backend/app/services/scheduler_manager.py` | 调度器管理 |
| `backend/app/services/task_execution_service.py` | 任务执行服务 |
| `backend/app/constants/task.py` | 任务类型常量 |
| `backend/app/models/scheduled_task.py` | 定时任务模型 |
| `backend/app/models/task_execution.py` | 任务执行记录模型 |

---

**文档版本**: v1.0
**最后更新**: 2025-12-05
**维护者**: NasFusion Team
