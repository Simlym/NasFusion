# 媒体库页面目录存储改造文档

## 📋 改造目标

将媒体库从「按文件存储」改为「按目录存储」,实现以下功能:
- **目录树浏览**: 左侧目录树 + 右侧详情的双栏布局
- **TV剧集聚合**: 按剧/季展示,不再按集产生大量记录
- **问题检测**: 快速识别缺海报、缺NFO、未识别等问题
- **增量扫描**: 支持变更扫描和全量重建,自动检测删除

---

## ✅ 已完成的后端改造

### 1. 数据库模型

#### 新建表: `media_directories`
位置: `backend/app/models/media_directory.py`

**核心字段**:
```python
- id: 主键
- directory_path: 目录完整路径(唯一索引)
- directory_name: 目录名称
- parent_id: 父目录ID(自关联)
- media_type: 媒体类型
- unified_table_name, unified_resource_id: 关联统一资源
- series_name, season_number, episode_count: TV剧集专用
- has_nfo, nfo_path, has_poster, poster_path, has_backdrop, backdrop_path: 元数据
- issue_flags: JSON格式问题标记
- total_files, total_size: 统计信息
- scanned_at, created_at, updated_at: 时间戳
```

#### 扩展表: `media_files`
位置: `backend/app/models/media_file.py`

**新增字段**:
```python
- media_directory_id: 外键关联到 media_directories.id
- status新增值: 'deleted' (文件不存在)
```

### 2. 常量定义

#### 新建: `backend/app/constants/media_directory.py`
```python
# 问题类型
ISSUE_TYPE_MISSING_POSTER = "missing_poster"
ISSUE_TYPE_MISSING_NFO = "missing_nfo"
ISSUE_TYPE_UNIDENTIFIED = "unidentified"
ISSUE_TYPE_DUPLICATE = "duplicate"
ISSUE_TYPE_MISSING_FILES = "missing_files"

# 扫描模式
SCAN_MODE_FULL = "full"          # 全量扫描
SCAN_MODE_INCREMENTAL = "incremental"  # 增量扫描
```

#### 更新: `backend/app/constants/media_file.py`
```python
MEDIA_FILE_STATUS_DELETED = "deleted"  # 已删除(文件不存在)
```

### 3. Service 层

#### 新建: `MediaDirectoryService`
位置: `backend/app/services/mediafile/media_directory_service.py`

**核心方法**:
- `get_tree(media_type, parent_id, load_children)` - 获取目录树
- `get_directory_detail(directory_id)` - 获取目录详情(含文件列表+统计)
- `sync_from_files(base_directory)` - 从media_files构建目录树
- `detect_issues(directory_id)` - 检测问题并更新issue_flags
- `delete_orphaned_directories(base_directory)` - 清理孤立目录

#### 扩展: `MediaFileService`
位置: `backend/app/services/mediafile/media_file_service.py`

**新增方法**:
- `delete_orphaned_records(base_directory)` - 删除不存在的文件记录

### 4. Task Handler

#### 修改: `MediaFileScanHandler`
位置: `backend/app/tasks/handlers/media_file_scan_handler.py`

**执行流程**:
```
1. 扫描文件 (0-40%)
2. 增量扫描时删除不存在的文件 (40-50%)
3. 构建目录树 (50-80%)
4. 检测问题 (80-90%)
5. 增量扫描时清理孤立目录 (90-95%)
6. 完成 (100%)
```

**新增参数**:
- `scan_mode`: "full" 或 "incremental"

### 5. Schema 定义

#### 新建: `backend/app/schemas/media_directory.py`
- `MediaDirectoryResponse` - 目录响应
- `DirectoryTreeNode` - 目录树节点(递归)
- `DirectoryDetailResponse` - 目录详情响应
- `SyncFromFilesRequest/Response` - 同步请求/响应
- `DetectIssuesRequest/Response` - 问题检测请求/响应

#### 扩展: `MediaFileScanRequest`
```python
class MediaFileScanRequest(BaseModel):
    directory: str
    recursive: bool = True
    media_type: Optional[str] = None
    scan_mode: Optional[str] = "full"  # 新增
```

### 6. API 路由

#### 新建: `/api/v1/media-directories`
位置: `backend/app/api/v1/media_directories.py`

**端点列表**:
```
GET  /tree                  # 获取目录树
GET  /{directory_id}        # 获取目录信息
GET  /{directory_id}/detail # 获取目录详情(含文件列表)
POST /sync                  # 从文件同步构建目录树
POST /detect-issues         # 检测问题
DELETE /{directory_id}      # 删除目录记录
```

#### 更新: `/api/v1/media-files/scan`
位置: `backend/app/api/v1/media_files.py`

**新增参数**: `scan_mode` (传递给handler)

---

## 📂 文件清单

### 新建文件
```
backend/app/models/media_directory.py
backend/app/constants/media_directory.py
backend/app/services/mediafile/media_directory_service.py
backend/app/schemas/media_directory.py
backend/app/api/v1/media_directories.py
```

### 修改文件
```
backend/app/models/media_file.py
backend/app/models/__init__.py
backend/app/constants/media_file.py
backend/app/constants/__init__.py
backend/app/services/mediafile/media_file_service.py
backend/app/tasks/handlers/media_file_scan_handler.py
backend/app/schemas/media_file.py
backend/app/api/v1/media_files.py
backend/app/api/v1/router.py
```

---

## 🚧 待完成的前端改造

### 1. API 封装

创建 `frontend/src/api/mediaDirectory.ts`:

```typescript
import request from '@/utils/request'

// 获取目录树
export function getDirectoryTree(params) {
  return request.get('/media-directories/tree', { params })
}

// 获取目录详情
export function getDirectoryDetail(id) {
  return request.get(`/media-directories/${id}/detail`)
}

// 同步目录树
export function syncDirectories(data) {
  return request.post('/media-directories/sync', data)
}

// 检测问题
export function detectIssues(data) {
  return request.post('/media-directories/detect-issues', data)
}
```

### 2. 前端组件

#### DirectoryTree.vue (左侧目录树)
路径: `frontend/src/components/MediaLibrary/DirectoryTree.vue`

**核心功能**:
- 使用 Element Plus `<el-tree>` 组件
- 懒加载子节点(通过 `load` 属性)
- 节点图标: 剧集/季度/问题标记
- 右键菜单: 刷新/重新扫描/检测问题
- 点击节点触发 `@node-click` 事件

#### DirectoryDetail.vue (右侧详情面板)
路径: `frontend/src/components/MediaLibrary/DirectoryDetail.vue`

**核心功能**:
- 目录统计卡片(文件数/总大小/剧集数)
- 元数据展示(海报/背景图)
- 文件列表表格(支持排序/筛选)
- 操作按钮(批量识别/刮削/整理)

#### ProblemFilter.vue (问题筛选器)
路径: `frontend/src/components/MediaLibrary/ProblemFilter.vue`

**核心功能**:
- 使用 `<el-check-tag>` 标签组
- 支持多选: 缺海报 / 缺NFO / 未识别 / 重复文件
- 高亮显示问题数量
- 筛选后传递给 DirectoryTree 组件

### 3. 页面重构

#### MediaLibrary.vue (主页面)
路径: `frontend/src/views/MediaLibrary.vue`

**布局设计**:
```vue
<template>
  <div class="media-library">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <el-radio-group v-model="mediaType">
        <el-radio-button label="movie">电影</el-radio-button>
        <el-radio-button label="tv_series">剧集</el-radio-button>
        <el-radio-button label="anime">动画</el-radio-button>
      </el-radio-group>

      <ProblemFilter v-model="selectedIssues" />

      <el-button @click="handleScan">扫描</el-button>
    </div>

    <!-- 双栏布局 -->
    <el-container class="main-content">
      <el-aside width="300px">
        <DirectoryTree
          :media-type="mediaType"
          :issues="selectedIssues"
          @node-click="handleNodeClick"
        />
      </el-aside>

      <el-main>
        <DirectoryDetail
          v-if="currentDirectoryId"
          :directory-id="currentDirectoryId"
        />
      </el-main>
    </el-container>
  </div>
</template>
```

---

## 🔄 数据迁移

创建 `backend/scripts/migrate_to_directory_storage.py`:

```python
"""
从现有media_files表构建media_directories表的迁移脚本
"""
import asyncio
from app.core.database import async_session_maker
from app.services.mediafile.media_directory_service import MediaDirectoryService

async def migrate():
    async with async_session_maker() as db:
        # 扫描所有媒体库目录
        base_dirs = ["./data/media"]

        for base_dir in base_dirs:
            print(f"开始同步目录: {base_dir}")
            result = await MediaDirectoryService.sync_from_files(db, base_dir)
            print(f"  新建: {result['created']} 个目录")
            print(f"  更新: {result['updated']} 个目录")

            print(f"检测问题...")
            issues = await MediaDirectoryService.detect_issues(db)
            print(f"  发现 {sum(issues.values())} 个问题")

if __name__ == "__main__":
    asyncio.run(migrate())
```

---

## 🎯 使用流程

### 1. 运行数据迁移
```bash
cd backend
python scripts/migrate_to_directory_storage.py
```

### 2. 扫描新文件
通过前端或API触发扫描:
```bash
POST /api/v1/media-files/scan
{
  "directory": "./data/media",
  "recursive": true,
  "scan_mode": "incremental"  # 或 "full"
}
```

### 3. 查看目录树
```bash
GET /api/v1/media-directories/tree?media_type=tv_series
```

### 4. 检测问题
```bash
POST /api/v1/media-directories/detect-issues
{
  "directory_id": null  # null表示检测所有目录
}
```

---

## 📊 数据流转

```
扫描流程:
  1. MediaFileScanHandler 扫描文件 → media_files 表
  2. MediaDirectoryService.sync_from_files() → media_directories 表
  3. MediaDirectoryService.detect_issues() → 更新 issue_flags
  4. 前端轮询 task_executions 表获取进度

增量扫描流程:
  1. 扫描文件(新增/更新)
  2. MediaFileService.delete_orphaned_records() 删除不存在的文件记录
  3. 同步目录树
  4. MediaDirectoryService.delete_orphaned_directories() 清理孤立目录
```

---

## 🔑 关键设计决策

1. **独立目录表**: 性能优化,支持目录级元数据
2. **三级层级**: 剧 → 季 → 集,符合文件系统结构
3. **自动检测**: 扫描时触发 + 前端筛选器
4. **直接删除**: 增量扫描删除不存在文件的数据库记录
5. **双向关联**: media_files.media_directory_id 和 MediaDirectory.files 关系

---

## 📌 待办事项

- [ ] 创建前端 mediaDirectory API 封装
- [ ] 创建前端 DirectoryTree 组件
- [ ] 创建前端 DirectoryDetail 组件
- [ ] 创建前端 ProblemFilter 组件
- [ ] 重构 MediaLibrary.vue 为双栏布局
- [ ] 创建数据迁移脚本
- [ ] 数据库迁移(添加新表)
- [ ] 前端测试和调优

---

**文档维护者**: Claude Code
**创建日期**: 2025-12-26
**版本**: v1.0
