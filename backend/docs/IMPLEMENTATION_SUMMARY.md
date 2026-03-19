# 下载任务与媒体文件关联功能实施总结

## 实施日期
2025-12-03

## 功能概述
完善 `media_file.download_task_id` 字段的赋值逻辑，实现下载完成时自动创建 MediaFile 记录，建立下载任务到媒体文件的完整追溯链。

## 核心改进

### 1. 数据模型增强
- ✅ `DownloadTask` 添加 `user_id` 字段（用于通知和权限控制）
- ✅ 添加 User ↔ DownloadTask 双向关系
- ✅ 修复 `MediaFile` 统一资源关联逻辑（使用多态字段）

### 2. 下载完成监听机制
- ✅ 新增定时任务类型：`TASK_TYPE_SYNC_DOWNLOAD_STATUS`
- ✅ 实现任务处理器：每分钟检查所有进行中的下载
- ✅ 下载完成时自动：
  - 更新 `completed_at` 时间戳
  - 创建 `MediaFile` 记录（`download_task_id` 自动赋值）
  - 发送下载完成通知
  - 关联统一资源（电影/电视剧）

### 3. 数据流完整性
```
用户创建下载（API + user_id）
  ↓
DownloadTask 记录（status=pending, user_id=X）
  ↓
提交到下载器（qBittorrent/Transmission）
  ↓
【定时任务每分钟轮询】
  ↓
检测到 progress=100%
  ↓
【触发完成逻辑】
  ├─ MediaFileService.create_from_download_task()
  │   └─ 创建 MediaFile（download_task_id ✅, unified_resource_id ✅）
  ├─ 发送通知给创建者（user_id）
  └─ 前端自动刷新
```

## 修改文件清单

### 模型层（3 个文件）
1. **backend/app/models/download_task.py** (143 行)
   - 添加 `user_id = Column(Integer, ForeignKey("users.id"))`
   - 添加 `user = relationship("User", back_populates="download_tasks")`

2. **backend/app/models/user.py** (114 行)
   - 添加 `download_tasks = relationship("DownloadTask", back_populates="user")`

3. **backend/app/services/media_file_service.py** (340-344 行)
   - 修复统一资源关联逻辑（从 `unified_movie_id` 改为多态字段）

### 服务层（2 个文件）
4. **backend/app/services/download_task_service.py** (628, 668 行)
   - 添加 `user_id` 到下载完成事件数据
   - 修复 `file_size` → `total_size` 字段引用

5. **backend/app/services/scheduler_manager.py** (888-940 行)
   - 新增 `TASK_TYPE_SYNC_DOWNLOAD_STATUS` 处理器
   - 导入 `TASK_TYPE_SYNC_DOWNLOAD_STATUS` 常量
   - 创建下载任务时保存 `user_id` (819 行)
   - 提取 `user_id` 参数 (600 行)

### API 层（1 个文件）
6. **backend/app/api/v1/download_tasks.py** (32-58 行)
   - 导入 `get_current_user` 依赖
   - 端点添加 `current_user: User` 参数
   - 传递 `user_id` 到任务参数

### 常量层（1 个文件）
7. **backend/app/constants/task.py** (15, 26, 38 行)
   - 新增 `TASK_TYPE_SYNC_DOWNLOAD_STATUS = "sync_download_status"`
   - 添加到 `TASK_TYPES` 列表
   - 添加到 `TASK_TYPE_DISPLAY_NAMES` 字典

### 数据库迁移（1 个文件）
8. **backend/scripts/migration/add_user_id_to_download_tasks.py** (新建)
   - SQLite 迁移脚本：添加 `user_id` 列和索引

### 初始化脚本（1 个文件）
9. **backend/scripts/init/init_download_sync_task.py** (新建)
   - 创建"监听下载完成"定时任务

---

## 部署步骤

### 步骤 1：运行数据库迁移

```bash
cd backend
python scripts/migration/add_user_id_to_download_tasks.py
```

**预期输出**：
```
开始迁移：添加 user_id 字段到 download_tasks 表
============================================================
[1/4] 检查字段是否已存在...
[2/4] 添加 user_id 列...
✓ user_id 列添加成功
[3/4] 创建索引...
✓ 索引创建成功
[4/4] 外键约束将在重启应用后生效（通过 SQLAlchemy 模型定义）

✓ 迁移完成！
============================================================

提示：请重启应用以使所有更改生效
```

### 步骤 2：初始化定时任务

```bash
python scripts/init/init_download_sync_task.py
```

**预期输出**：
```
初始化下载状态同步定时任务
============================================================
[1/2] 检查任务是否已存在...
[2/2] 创建新任务...
✓ 任务已创建: 监听下载完成 (ID: X)

============================================================
✓ 初始化完成！

任务详情:
  - 任务名称: 监听下载完成
  - 任务类型: sync_download_status
  - 调度类型: 固定间隔
  - 执行频率: 每 1 分钟
  - 优先级: 2
  - 状态: 启用

提示：重启应用后任务将自动运行
```

### 步骤 3：重启应用

```bash
# 停止后端服务
# 重新启动
python -m app.main
```

### 步骤 4：验证功能

#### 4.1 检查数据库字段
```sql
-- 检查 download_tasks 表结构
PRAGMA table_info(download_tasks);
-- 应该看到 user_id 字段

-- 检查索引
SELECT name FROM sqlite_master
WHERE type='index' AND tbl_name='download_tasks';
-- 应该看到 ix_download_tasks_user_id
```

#### 4.2 检查定时任务
```sql
-- 查询定时任务
SELECT * FROM scheduled_tasks
WHERE task_type = 'sync_download_status';
-- 应该看到 1 条记录，enabled=1
```

#### 4.3 创建测试下载任务

通过前端或 API 创建一个下载任务：

```bash
POST /api/v1/download-tasks
{
  "pt_resource_id": 123,
  "downloader_config_id": 1,
  "save_path": "./data/downloads/Movies",
  "torrent_name": "测试电影",
  ...
}
```

**观察点**：
1. 返回 `execution_id`
2. `download_tasks` 表中应该有记录，且 `user_id` 不为空

#### 4.4 等待下载完成

监控以下内容：

```sql
-- 1. 查看任务执行历史
SELECT * FROM task_executions
WHERE task_type = 'sync_download_status'
ORDER BY started_at DESC
LIMIT 5;

-- 2. 查看下载任务状态
SELECT id, torrent_name, status, progress, completed_at
FROM download_tasks
ORDER BY created_at DESC
LIMIT 5;

-- 3. 查看媒体文件记录
SELECT id, file_name, download_task_id, match_method, match_confidence, status
FROM media_files
WHERE download_task_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;
```

#### 4.5 验证完整流程

**预期结果**：
- ✅ 下载完成后 `completed_at` 自动更新
- ✅ `media_files` 表中自动创建记录
- ✅ `media_file.download_task_id` 有值
- ✅ `media_file.match_method` = "from_download"
- ✅ `media_file.match_confidence` = 95
- ✅ `media_file.unified_table_name` 和 `unified_resource_id` 正确关联
- ✅ 用户收到下载完成通知

---

## 验证 SQL 查询

### 查询 1：检查关联完整性
```sql
SELECT
    mf.id AS media_file_id,
    mf.file_name,
    mf.download_task_id,
    mf.match_method,
    mf.match_confidence,
    mf.status AS media_status,
    mf.unified_table_name,
    mf.unified_resource_id,
    dt.task_hash,
    dt.torrent_name,
    dt.user_id,
    dt.completed_at,
    dt.status AS task_status
FROM media_files mf
LEFT JOIN download_tasks dt ON mf.download_task_id = dt.id
WHERE mf.download_task_id IS NOT NULL
ORDER BY mf.created_at DESC
LIMIT 10;
```

### 查询 2：统计下载来源的文件
```sql
SELECT
    match_method,
    COUNT(*) AS file_count,
    AVG(match_confidence) AS avg_confidence
FROM media_files
GROUP BY match_method;
```

**预期结果**：
```
| match_method     | file_count | avg_confidence |
|------------------|------------|----------------|
| from_download    | XX         | 95.0           |
| from_filename    | XX         | 60-80          |
| ...              | ...        | ...            |
```

### 查询 3：检查通知发送情况
```sql
SELECT
    ni.id,
    ni.event_type,
    ni.title,
    ni.user_id,
    ni.is_read,
    ni.created_at,
    dt.torrent_name
FROM notification_internal ni
LEFT JOIN download_tasks dt ON ni.related_id = dt.id
WHERE ni.event_type = 'download_completed'
ORDER BY ni.created_at DESC
LIMIT 10;
```

---

## 性能考虑

### 定时任务优化
- **查询优化**：只查询 `status IN ('pending', 'downloading')` 的任务
- **索引**：`ix_download_tasks_status` 已存在（第 129 行）
- **频率调整**：可根据实际需求调整为 2-5 分钟
  ```python
  # 在 init_download_sync_task.py 中修改
  trigger_config={"minutes": 2}  # 改为 2 分钟
  ```

### 并发控制
- 定时任务与手动同步不会冲突（幂等性保证）
- MediaFile 创建时有文件路径去重检查（第 184-188 行）

---

## 回滚方案

如遇问题需要回滚：

### 1. 禁用定时任务
```sql
UPDATE scheduled_tasks
SET enabled = 0
WHERE task_type = 'sync_download_status';
```

### 2. 移除 user_id 字段（可选）
```sql
-- SQLite 不支持 DROP COLUMN，需要重建表
-- 建议保留字段，设为 nullable
```

### 3. 恢复代码
```bash
git checkout HEAD -- backend/app/models/download_task.py
git checkout HEAD -- backend/app/services/download_task_service.py
# ... 其他文件
```

---

## 已知限制

1. **不支持实时 Webhook**：当前使用轮询机制（每 1 分钟），最多延迟 1 分钟。未来可考虑实现下载器 Webhook 回调（qBittorrent `torrent finished` 事件）。

2. **历史数据 user_id 为空**：迁移前创建的下载任务 `user_id = NULL`，不影响功能，通知会跳过这些任务。

3. **SQLite 外键限制**：外键约束通过 SQLAlchemy 模型定义，不在数据库层强制。

---

## 文档更新建议

### 更新 CLAUDE.md

在"核心开发规范"章节添加：

```markdown
### 11. 下载任务生命周期

**自动流程**：
- 下载完成后，系统自动创建 MediaFile 记录
- download_task_id 自动关联
- 无需手动"扫描目录"

**来源追溯**：
- `match_method = "from_download"`: 来自下载任务（准确度 95）
- `match_method = "from_filename"`: 来自目录扫描（准确度 60-80）

**通知系统**：
- 下载完成自动通知创建者（user_id）
- 事件类型：`NOTIFICATION_EVENT_DOWNLOAD_COMPLETED`
```

---

## 贡献者
- 实施者：Claude (Anthropic)
- 审核者：待定

---

## 附录：关键代码片段

### MediaFile 创建逻辑
```python
# backend/app/services/download_task_service.py:428-435
if newly_completed:
    media_files = await MediaFileService.create_from_download_task(db, task)
    await TaskExecutionService.append_log(
        db, execution.id,
        f"✓ 自动创建 {len(media_files)} 个媒体文件记录"
    )
```

### download_task_id 赋值
```python
# backend/app/services/media_file_service.py:320-330
media_file = MediaFile(
    file_path=str(file_path),
    file_name=file_path.name,
    directory=str(file_path.parent),
    file_size=file_path.stat().st_size,
    file_type=file_type,
    download_task_id=download_task.id if download_task else None,  # ✅ 关键赋值
    match_method=MATCH_METHOD_FROM_DOWNLOAD,
    match_confidence=95,
    status=MEDIA_FILE_STATUS_DISCOVERED,
)
```

### 定时任务处理器
```python
# backend/app/services/scheduler_manager.py:888-940
elif task.task_type == TASK_TYPE_SYNC_DOWNLOAD_STATUS:
    tasks = await db.execute(
        select(DownloadTask).where(
            DownloadTask.status.in_(["pending", "downloading"])
        )
    )
    for download_task in tasks.scalars().all():
        is_completed = await DownloadTaskService.sync_task_status(db, download_task)
        if is_completed:
            completed_count += 1
```

---

**实施状态**：✅ 已完成代码修改，待运行迁移和验证
