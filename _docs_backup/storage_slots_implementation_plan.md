# NasFusion 存储挂载点系统 - 详细实施计划

## 📋 项目概述

**目标**: 实现基于挂载点（Mount）的存储配置系统，支持多盘聚合、灵活的下载/媒体库映射、硬链接优化。

**预计工期**: 6 周
**开发模式**: 分阶段迭代实施
**测试策略**: 每阶段完成后进行单元测试和集成测试

---

## 🎯 第一阶段：数据库设计（第 1 周）

### 任务 1.1: 创建 StorageMount 模型

**文件**: `backend/app/models/storage_mount.py`

**实施步骤**:

1. **创建模型文件** (30分钟)
   ```bash
   # 创建文件
   touch backend/app/models/storage_mount.py
   ```

2. **编写模型代码** (2小时)
   - 添加文件头部导入
   - 定义 `StorageMount` 类
   - 添加所有字段（参考计划文档第32-107行）
   - 添加约束和索引
   - 添加 `__repr__` 方法

3. **验证检查** (30分钟)
   - [ ] 所有导入语句正确
   - [ ] 字段类型正确
   - [ ] 约束条件完整
   - [ ] 索引定义完整
   - [ ] 无语法错误

**关键代码片段**:
```python
from app.constants.media import MEDIA_TYPES
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, Index, CheckConstraint
from sqlalchemy.sql import func
from app.models.base import Base

class StorageMount(Base):
    __tablename__ = "storage_mounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    mount_type = Column(String(20), nullable=False)  # 'download' | 'library'
    container_path = Column(String(500), nullable=False)
    host_path = Column(String(500), nullable=True)
    device_id = Column(Integer, nullable=True)
    media_category = Column(String(50), nullable=True)  # movie, tv, music, etc.
    priority = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)
    is_accessible = Column(Boolean, default=True)
    total_space = Column(BigInteger, nullable=True)
    used_space = Column(BigInteger, nullable=True)
    free_space = Column(BigInteger, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**预计时间**: 3小时

---

### 任务 1.2: 创建数据库迁移脚本

**文件**: `backend/alembic/versions/[timestamp]_add_storage_mounts.py`

**实施步骤**:

1. **生成迁移文件** (15分钟)
   ```bash
   cd backend
   alembic revision -m "add_storage_mounts"
   ```

2. **编写 upgrade() 函数** (1.5小时)
   - 复制计划文档第130-158行的 `op.create_table()` 代码
   - 添加所有索引创建语句（第160-167行）
   - 验证字段定义与模型一致

3. **编写 downgrade() 函数** (15分钟)
   ```python
   def downgrade():
       op.drop_table('storage_mounts')
   ```

4. **测试迁移** (1小时)
   ```bash
   # 执行迁移
   alembic upgrade head

   # 验证表结构
   python -c "from app.models import StorageMount; print(StorageMount.__table__)"

   # 回滚测试
   alembic downgrade -1
   alembic upgrade head
   ```

**验证检查**:
- [ ] 迁移文件生成成功
- [ ] upgrade 执行无错误
- [ ] 数据库中表创建成功
- [ ] 所有索引创建成功
- [ ] downgrade 回滚成功

**预计时间**: 3小时

---

### 任务 1.3: 更新模型导出

**文件**: `backend/app/models/__init__.py`

**实施步骤**:

1. **添加导入语句** (5分钟)
   ```python
   from app.models.storage_mount import StorageMount

   __all__ = [
       # ... 现有模型 ...
       "StorageMount",
   ]
   ```

2. **验证导入** (5分钟)
   ```bash
   python -c "from app.models import StorageMount; print('Import successful')"
   ```

**预计时间**: 10分钟

---

## 🔧 部署模式配置说明

### 自动检测机制

系统通过检测 `/.dockerenv` 文件自动判断运行环境：

```python
import os

def is_docker_environment() -> bool:
    """检测是否在 Docker 容器中运行"""
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
```

### Docker 部署模式

**配置文件**: 项目根目录 `.env`

**挂载点扫描逻辑**:
- 自动扫描 `/app/data/downloads/mount_*` 目录
- 自动扫描 `/app/data/library/mount_*` 目录
- 从环境变量读取宿主机路径（如 `DOWNLOAD_MOUNT_1_HOST`、`LIBRARY_MOUNT_1_HOST`）

### 本地/源码部署模式

**配置文件**: `backend/.env`

**新增环境变量**:
```env
# ==============================================================================
# 存储挂载点配置（本地/源码部署）
# ==============================================================================
# 说明：
# 1. 本地部署模式下，直接配置实际路径
# 2. 多个路径使用英文逗号分隔
# 3. 路径必须存在且有读写权限
# ==============================================================================

# 下载目录路径（多个用逗号分隔）
STORAGE_DOWNLOAD_PATHS=./data/downloads,/mnt/disk2/downloads

# 媒体库目录配置
# 格式：路径:分类:是否默认
# 分类可选：movie, tv, music, book, anime, adult, game, other
STORAGE_LIBRARY_PATHS=./data/library/movies:movie:true,./data/library/tv:tv:true,./data/library/music:music:false
```

**挂载点扫描逻辑**:
- 解析 `STORAGE_DOWNLOAD_PATHS` 环境变量
- 解析 `STORAGE_LIBRARY_PATHS` 环境变量（含分类和默认标识）
- 本地模式下 `container_path` = `host_path`（无需映射）

### 配置对比

| 特性 | Docker 部署 | 本地部署 |
|------|-------------|----------|
| 配置文件 | 根目录 `.env` | `backend/.env` |
| 路径映射 | 需要（容器 ↔ 宿主机） | 不需要（路径相同） |
| 挂载点目录 | 预定义结构 `mount_*` | 灵活配置任意路径 |
| 环境变量 | `DOWNLOAD_MOUNT_*_HOST` | `STORAGE_DOWNLOAD_PATHS` |
| 分类配置 | Web UI 手动配置 | 环境变量直接指定 |

---

## ⚙️ 第二阶段：后端服务层（第 2 周）

### 任务 2.1: 创建 StorageMountService

**文件**: `backend/app/services/storage/storage_mount_service.py`

**实施步骤**:

1. **创建目录和文件** (10分钟)
   ```bash
   mkdir -p backend/app/services/storage
   touch backend/app/services/storage/__init__.py
   touch backend/app/services/storage/storage_mount_service.py
   ```

2. **实现核心方法 - 第1组：扫描相关** (4小时)

   **2.1.1 实现 `scan_and_init_mounts()`** (1.5小时)
   - 实现下载挂载点扫描逻辑
   - 实现媒体库挂载点扫描逻辑

   **2.1.2 实现 `_create_or_update_mount()`** (1.5小时)
   - 实现挂载点创建逻辑
   - 实现挂载点更新逻辑

   **2.1.3 实现 `_get_host_path_from_env()`** (1小时)
   - 处理标准格式环境变量
   - 处理自定义格式环境变量

3. **实现核心方法 - 第2组：查询推荐** (3小时)

   **2.2.1 实现 `get_download_mounts_for_media()`** (1.5小时)
   - 实现目标媒体库挂载点查找
   - 实现同盘优先排序

   **2.2.2 实现 `get_library_mounts_by_category()`** (1小时)
   - 实现按媒体分类查询
   - 实现优先级排序

   **2.2.3 实现 `get_organize_target()`** (30分钟)
   - 实现同盘优先整理目标查找

4. **实现核心方法 - 第3组：工具方法** (2小时)

   **2.3.1 实现 `check_same_disk()`** (30分钟)
   - 实现设备号比较逻辑

   **2.3.2 实现 `refresh_disk_info()`** (1小时)
   - 实现磁盘空间信息刷新

   **2.3.3 实现 `update_mount_config()`** (30分钟)
   - 实现挂载点配置更新
   - 处理默认挂载点唯一性

**验证检查**:
- [ ] 所有方法实现完整
- [ ] 类型注解正确
- [ ] 异常处理完善
- [ ] 日志记录充足
- [ ] 单元测试通过

**预计时间**: 9小时

---

### 任务 2.2: 集成现有服务

**实施步骤**:

**2.2.1 修改 DownloadTaskService** (1小时)

**文件**: `backend/app/services/download/download_task_service.py`

1. 添加导入:
   ```python
   from app.services.storage.storage_mount_service import StorageMountService
   ```

2. 修改 `create()` 方法中的路径选择逻辑:
   - 在 `create()` 方法中定位路径选择代码
   - 替换为挂载点推荐逻辑

**2.2.2 修改 MediaOrganizerService** (1.5小时)

**文件**: `backend/app/services/mediafile/media_organizer_service.py`

1. 添加导入:
   ```python
   from app.services.storage.storage_mount_service import StorageMountService
   ```

2. 修改 `organize_media_file()` 方法:
   - 替换目标路径获取逻辑
   - 添加同盘检测逻辑
   - 根据检测结果选择整理模式

**验证检查**:
- [ ] 导入语句正确
- [ ] 路径选择逻辑正确
- [ ] 同盘检测工作正常
- [ ] 整理模式选择正确
- [ ] 单元测试通过

**预计时间**: 2.5小时

---

### 任务 2.3: 系统启动集成

**文件**: `backend/app/core/init.py`

**实施步骤**:

1. **添加导入** (5分钟)
   ```python
   from app.services.storage.storage_mount_service import StorageMountService
   ```

2. **修改 init_app() 函数** (30分钟)
   - 在适当位置添加挂载点扫描逻辑
   - 添加日志记录

3. **测试启动流程** (30分钟)
   ```bash
   # 创建测试挂载点目录
   mkdir -p data/downloads/mount_1
   mkdir -p data/library/mount_1

   # 启动应用
   python -m app.main

   # 检查日志输出
   # 验证挂载点扫描成功
   ```

**验证检查**:
- [ ] 应用启动成功
- [ ] 挂载点扫描日志正确
- [ ] 数据库记录创建成功

**预计时间**: 1小时

---

## 🔌 第三阶段：API 接口（第 3 周）

### 任务 3.1: 创建 Schema 定义

**文件**: `backend/app/schemas/storage_mount.py`

**实施步骤**:

1. **创建文件** (10分钟)
   ```bash
   touch backend/app/schemas/storage_mount.py
   ```

2. **编写 Schema 类** (2小时)
   - 实现 `StorageMountBase`
   - 实现 `StorageMountUpdate`
   - 实现 `StorageMountResponse`
   - 实现 `DownloadMountRecommendation`
   - 实现 `SameDiskCheckResponse`
   - 实现 `StorageStatsResponse`

3. **更新 schemas/__init__.py** (5分钟)
   ```python
   from app.schemas.storage_mount import (
       StorageMountBase,
       StorageMountUpdate,
       StorageMountResponse,
       DownloadMountRecommendation,
       SameDiskCheckResponse,
       StorageStatsResponse,
   )
   ```

**预计时间**: 2.5小时

---

### 任务 3.2: 创建 API 端点

**文件**: `backend/app/api/v1/storage_mounts.py`

**实施步骤**:

1. **创建文件和基础结构** (30分钟)
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from sqlalchemy.ext.asyncio import AsyncSession

   from app.core.deps import get_async_db
   from app.services.storage.storage_mount_service import StorageMountService
   from app.schemas.storage_mount import *

   router = APIRouter(prefix="/storage-mounts", tags=["storage-mounts"])
   ```

2. **实现基础 CRUD 端点** (2小时)

   **3.2.1 GET /storage-mounts** - 列表查询
   ```python
   @router.get("", response_model=dict)
   async def list_storage_mounts(
       mount_type: Optional[str] = None,
       media_category: Optional[str] = None,
       device_id: Optional[int] = None,
       is_enabled: bool = True,
       db: AsyncSession = Depends(get_async_db)
   ):
       # 实现列表查询逻辑
   ```

   **3.2.2 GET /storage-mounts/{id}** - 获取详情
   **3.2.3 PATCH /storage-mounts/{id}** - 更新配置

3. **实现功能性端点** (3小时)

   **3.2.4 POST /storage-mounts/scan** - 手动扫描
   **3.2.5 POST /storage-mounts/refresh-disk-info** - 刷新磁盘信息
   **3.2.6 GET /storage-mounts/download-mounts** - 获取下载挂载点
   **3.2.7 GET /storage-mounts/library-mounts** - 获取媒体库挂载点
   **3.2.8 POST /storage-mounts/check-same-disk** - 同盘检测
   **3.2.9 GET /storage-mounts/stats** - 统计信息

4. **注册路由** (15分钟)

   **文件**: `backend/app/api/v1/__init__.py`
   ```python
   from app.api.v1 import storage_mounts

   # 在 create_api_router() 中添加
   api_router.include_router(storage_mounts.router)
   ```

**验证检查**:
- [ ] 所有端点实现完整
- [ ] 请求/响应 Schema 正确
- [ ] 权限控制适当
- [ ] 错误处理完善
- [ ] API 文档生成正确

**预计时间**: 6小时

---

### 任务 3.3: API 测试

**实施步骤**:

1. **手动测试** (2小时)
   - 启动开发服务器
   - 访问 http://localhost:8000/docs
   - 测试所有端点
   - 验证响应格式

2. **编写集成测试** (2小时)

   **文件**: `backend/tests/api/test_storage_mounts.py`
   ```python
   import pytest
   from httpx import AsyncClient

   @pytest.mark.asyncio
   async def test_list_storage_mounts(client: AsyncClient):
       response = await client.get("/api/v1/storage-mounts")
       assert response.status_code == 200
       # ... 更多断言
   ```

**预计时间**: 4小时

---

## 🎨 第四阶段:前端 UI 实现（第 4 周）

### 任务 4.1: 创建 API 客户端模块

**文件**: `frontend/src/api/modules/storage.ts`

**实施步骤**:

1. **创建文件** (10分钟)
   ```bash
   touch frontend/src/api/modules/storage.ts
   ```

2. **定义接口类型** (1小时)
   ```typescript
   export interface StorageMount {
     id: number
     name: string
     mount_type: 'download' | 'library'
     container_path: string
     host_path?: string
     device_id?: number
     media_category?: string
     priority: number
     is_default: boolean
     is_enabled: boolean
     is_accessible: boolean
     total_space?: number
     used_space?: number
     free_space?: number
     description?: string
     is_same_disk?: boolean
   }

   export interface StorageMountUpdate {
     media_category?: string
     priority?: number
     is_default?: boolean
     description?: string
     is_enabled?: boolean
     host_path?: string
   }
   ```

3. **实现 API 函数** (2小时)
   ```typescript
   export function getStorageMounts(params?: {
     mount_type?: string
     media_category?: string
     device_id?: number
     is_enabled?: boolean
   }) {
     return request.get<{ total: number; items: StorageMount[] }>(
       '/storage-mounts',
       { params }
     )
   }

   export function getDownloadMountsForMedia(params: {
     media_category: string
     library_mount_id?: number
   }) {
     return request.get<{ mounts: StorageMount[] }>(
       '/storage-mounts/download-mounts',
       { params }
     )
   }

   export function updateStorageMount(id: number, data: StorageMountUpdate) {
     return request.patch<StorageMount>(`/storage-mounts/${id}`, data)
   }

   export function scanStorageMounts() {
     return request.post('/storage-mounts/scan')
   }

   export function refreshDiskInfo(mount_id?: number) {
     return request.post('/storage-mounts/refresh-disk-info', { mount_id })
   }

   export function checkSameDisk(path1: string, path2: string) {
     return request.post('/storage-mounts/check-same-disk', {
       path1,
       path2
     })
   }
   ```

**预计时间**: 3小时

---

### 任务 4.2: 创建存储挂载点管理页面

**文件**: `frontend/src/views/StorageMounts.vue`

**实施步骤**:

1. **创建文件和基础结构** (1小时)
   ```vue
   <template>
     <div class="storage-mounts-page">
       <el-card>
         <template #header>
           <div class="card-header">
             <span>存储挂载点管理</span>
             <div>
               <el-button @click="handleScan">扫描目录</el-button>
               <el-button @click="handleRefresh">刷新</el-button>
             </div>
           </div>
         </template>

         <!-- Tab 切换 -->
         <el-tabs v-model="activeTab">
           <el-tab-pane label="按磁盘查看" name="by-disk">
             <!-- 按设备分组显示 -->
           </el-tab-pane>

           <el-tab-pane label="按类型查看" name="by-type">
             <!-- 按挂载点类型显示 -->
           </el-tab-pane>

           <el-tab-pane label="所有挂载点" name="all">
             <!-- 列表显示 -->
           </el-tab-pane>
         </el-tabs>
       </el-card>
     </div>
   </template>
   ```

2. **实现"按磁盘查看" Tab** (3小时)
   ```vue
   <template>
     <div v-for="device in groupedByDevice" :key="device.device_id">
       <el-collapse>
         <el-collapse-item>
           <template #title>
             <div class="device-header">
               <span>设备 ID: {{ device.device_id }}</span>
               <span>容量: {{ formatSize(device.total_space) }}</span>
             </div>
           </template>

           <!-- 下载挂载点 -->
           <div class="mount-section">
             <h4>下载挂载点 ({{ device.downloadMounts.length }})</h4>
             <el-table :data="device.downloadMounts">
               <!-- 挂载点列表 -->
             </el-table>
           </div>

           <!-- 媒体库挂载点 -->
           <div class="mount-section">
             <h4>媒体库挂载点 ({{ device.libraryMounts.length }})</h4>
             <el-table :data="device.libraryMounts">
               <!-- 挂载点列表 -->
             </el-table>
           </div>
         </el-collapse-item>
       </el-collapse>
     </div>
   </template>
   ```

3. **实现挂载点列表表格** (3小时)
   ```vue
   <el-table :data="mounts">
     <el-table-column label="挂载点名称" prop="name" width="150" />

     <el-table-column label="容器路径" prop="container_path" width="250" />

     <el-table-column label="宿主机路径" width="300">
       <template #default="{ row }">
         <el-input
           v-model="row.host_path"
           placeholder="未配置"
           :disabled="!editingMountId || editingMountId !== row.id"
         >
           <template #append>
             <el-button
               v-if="!editingMountId || editingMountId !== row.id"
               @click="startEdit(row)"
             >
               编辑
             </el-button>
             <el-button
               v-else
               type="primary"
               @click="saveHostPath(row)"
             >
               保存
             </el-button>
           </template>
         </el-input>
       </template>
     </el-table-column>

     <el-table-column label="设备ID" prop="device_id" width="100" />

     <el-table-column label="挂载点类型" width="100">
       <template #default="{ row }">
         <el-tag :type="row.mount_type === 'download' ? 'primary' : 'success'">
           {{ row.mount_type === 'download' ? '下载' : '媒体库' }}
         </el-tag>
       </template>
     </el-table-column>

     <el-table-column label="媒体分类" width="120">
       <template #default="{ row }">
         <el-select
           v-if="row.mount_type === 'library'"
           v-model="row.media_category"
           placeholder="选择分类"
           @change="updateMount(row)"
         >
           <el-option label="电影" value="movie" />
           <el-option label="电视剧" value="tv" />
           <el-option label="音乐" value="music" />
           <el-option label="书籍" value="book" />
           <el-option label="动漫" value="anime" />
           <el-option label="成人" value="adult" />
           <el-option label="游戏" value="game" />
           <el-option label="其他" value="other" />
         </el-select>
         <span v-else>-</span>
       </template>
     </el-table-column>

     <el-table-column label="优先级" width="120">
       <template #default="{ row }">
         <el-input-number
           v-if="row.mount_type === 'library'"
           v-model="row.priority"
           :min="0"
           :max="1000"
           @change="updateMount(row)"
         />
         <span v-else>-</span>
       </template>
     </el-table-column>

     <el-table-column label="默认" width="80" align="center">
       <template #default="{ row }">
         <el-switch
           v-if="row.mount_type === 'library' && row.media_category"
           v-model="row.is_default"
           @change="updateMount(row)"
         />
       </template>
     </el-table-column>

     <el-table-column label="磁盘空间" width="200">
       <template #default="{ row }">
         <div v-if="row.total_space">
           <el-progress
             :percentage="((row.used_space / row.total_space) * 100).toFixed(1)"
             :color="getSpaceColor(row.used_space / row.total_space)"
           />
           <div class="space-text">
             {{ formatSize(row.free_space) }} / {{ formatSize(row.total_space) }}
           </div>
         </div>
       </template>
     </el-table-column>

     <el-table-column label="备注" width="200">
       <template #default="{ row }">
         <el-input
           v-model="row.description"
           placeholder="输入备注"
           @blur="updateMount(row)"
         />
       </template>
     </el-table-column>

     <el-table-column label="状态" width="100">
       <template #default="{ row }">
         <el-tag :type="row.is_accessible ? 'success' : 'danger'">
           {{ row.is_accessible ? '正常' : '异常' }}
         </el-tag>
       </template>
     </el-table-column>

     <el-table-column label="操作" width="150" fixed="right">
       <template #default="{ row }">
         <el-button
           size="small"
           @click="refreshMountDiskInfo(row.id)"
         >
           刷新容量
         </el-button>
         <el-switch
           v-model="row.is_enabled"
           active-text="启用"
           inactive-text="禁用"
           @change="updateMount(row)"
         />
       </template>
     </el-table-column>
   </el-table>
   ```

4. **实现脚本逻辑** (3小时)
   ```typescript
   import { ref, reactive, onMounted, computed } from 'vue'
   import { ElMessage } from 'element-plus'
   import {
     getStorageMounts,
     updateStorageMount,
     scanStorageMounts,
     refreshDiskInfo
   } from '@/api/modules/storage'
   import type { StorageMount } from '@/api/modules/storage'

   const activeTab = ref('by-disk')
   const mounts = ref<StorageMount[]>([])
   const loading = ref(false)
   const editingMountId = ref<number | null>(null)

   // 按设备分组
   const groupedByDevice = computed(() => {
     const groups = new Map()
     mounts.value.forEach(mount => {
       if (!groups.has(mount.device_id)) {
         groups.set(mount.device_id, {
           device_id: mount.device_id,
           downloadMounts: [],
           libraryMounts: [],
           total_space: 0,
           free_space: 0
         })
       }
       const group = groups.get(mount.device_id)
       if (mount.mount_type === 'download') {
         group.downloadMounts.push(mount)
       } else {
         group.libraryMounts.push(mount)
       }
       if (mount.total_space) {
         group.total_space = Math.max(group.total_space, mount.total_space)
         group.free_space = Math.max(group.free_space, mount.free_space)
       }
     })
     return Array.from(groups.values())
   })

   // 加载挂载点列表
   async function loadMounts() {
     loading.value = true
     try {
       const res = await getStorageMounts()
       mounts.value = res.data.items
     } catch (error: any) {
       ElMessage.error('加载挂载点列表失败')
     } finally {
       loading.value = false
     }
   }

   // 更新挂载点配置
   async function updateMount(mount: StorageMount) {
     try {
       await updateStorageMount(mount.id, {
         media_category: mount.media_category,
         priority: mount.priority,
         is_default: mount.is_default,
         description: mount.description,
         is_enabled: mount.is_enabled
       })
       ElMessage.success('更新成功')
     } catch (error: any) {
       ElMessage.error('更新失败')
       await loadMounts() // 重新加载
     }
   }

   // 扫描目录
   async function handleScan() {
     loading.value = true
     try {
       await scanStorageMounts()
       ElMessage.success('扫描完成')
       await loadMounts()
     } catch (error: any) {
       ElMessage.error('扫描失败')
     } finally {
       loading.value = false
     }
   }

   // 刷新磁盘信息
   async function refreshMountDiskInfo(mountId: number) {
     try {
       await refreshDiskInfo(mountId)
       ElMessage.success('刷新成功')
       await loadMounts()
     } catch (error: any) {
       ElMessage.error('刷新失败')
     }
   }

   // 格式化文件大小
   function formatSize(bytes: number): string {
     if (!bytes) return '-'
     const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
     const i = Math.floor(Math.log(bytes) / Math.log(1024))
     return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
   }

   // 获取空间颜色
   function getSpaceColor(ratio: number): string {
     if (ratio < 0.6) return '#67C23A'
     if (ratio < 0.8) return '#E6A23C'
     return '#F56C6C'
   }

   onMounted(() => {
     loadMounts()
   })
   ```

5. **添加样式** (30分钟)
   ```vue
   <style scoped>
   .storage-mounts-page {
     padding: 20px;
   }

   .card-header {
     display: flex;
     justify-content: space-between;
     align-items: center;
   }

   .device-header {
     display: flex;
     gap: 20px;
     align-items: center;
   }

   .mount-section {
     margin: 20px 0;
   }

   .space-text {
     font-size: 12px;
     color: #909399;
     margin-top: 4px;
   }
   </style>
   ```

**预计时间**: 10小时

---

### 任务 4.3: 修改下载对话框

**文件**: `frontend/src/components/download/DownloadDialog.vue`

**实施步骤**:

1. **更新导入** (10分钟)
   ```typescript
   import { getDownloadMountsForMedia } from '@/api/modules/storage'
   ```

2. **修改路径加载逻辑** (1小时)
   ```typescript
   // NEW: 从存储挂载点 API 获取推荐下载路径
   async function loadCategoryPaths(downloader: DownloaderConfig) {
     if (!props.resource?.category) {
       availablePaths.value = []
       form.save_path = ''
       return
     }

     try {
       const response = await getDownloadMountsForMedia({
         media_category: props.resource.category
       })

       const mounts = response.data.mounts || []

       // 转换为 CategoryPath 格式
       availablePaths.value = mounts.map((mount: any) => ({
         path: mount.container_path,
         is_default: mount.is_default,
         is_same_disk: mount.is_same_disk,
         free_space: mount.free_space
       }))

       // 自动选择默认路径
       const defaultPath = availablePaths.value.find(p => p.is_default)
       if (defaultPath) {
         form.save_path = defaultPath.path
       } else if (availablePaths.value.length > 0) {
         form.save_path = availablePaths.value[0].path
       } else {
         form.save_path = `/downloads/${props.resource.category}`
       }
     } catch (error: any) {
       console.error('加载下载路径失败:', error)
       // 使用默认值
       form.save_path = `/downloads/${props.resource.category}`
       availablePaths.value = [{ path: form.save_path, is_default: true }]
     }
   }
   ```

3. **增强 UI 显示** (1小时)
   ```vue
   <el-form-item label="保存路径" prop="save_path">
     <el-select
       v-model="form.save_path"
       placeholder="请选择保存路径"
       style="width: 100%"
       allow-create
       filterable
     >
       <el-option
         v-for="path in availablePaths"
         :key="path.path"
         :label="path.path"
         :value="path.path"
       >
         <div style="display: flex; justify-content: space-between; align-items: center;">
           <span>{{ path.path }}</span>
           <div style="display: flex; gap: 8px; align-items: center;">
             <el-tag v-if="path.is_default" type="success" size="small">
               默认
             </el-tag>
             <el-tag v-if="path.is_same_disk" type="primary" size="small">
               💾 同盘
             </el-tag>
             <span v-if="path.free_space" style="font-size: 12px; color: #909399;">
               剩余: {{ formatSize(path.free_space) }}
             </span>
           </div>
         </div>
       </el-option>
     </el-select>
     <div style="font-size: 12px; color: #909399; margin-top: 4px">
       {{ resource?.category ? `当前分类：${getCategoryLabel(resource.category)}` : '' }}
       <span v-if="form.save_path && isSameDiskPath(form.save_path)" style="color: #409EFF; margin-left: 10px;">
         ✓ 支持硬链接整理
       </span>
     </div>
   </el-form-item>
   ```

**验证检查**:
- [ ] 路径加载正确
- [ ] 同盘标识显示正常
- [ ] 剩余空间显示正确
- [ ] 默认路径自动选中
- [ ] UI 交互流畅

**预计时间**: 3小时

---

### 任务 4.4: 添加路由配置

**文件**: `frontend/src/router/index.ts`

**实施步骤**:

1. **添加路由** (15分钟)
   ```typescript
   {
     path: '/storage-mounts',
     name: 'StorageMounts',
     component: () => import('@/views/StorageMounts.vue'),
     meta: {
       title: '存储挂载点管理',
       requiresAuth: true,
       icon: 'HardDrive'
     }
   }
   ```

2. **更新菜单配置** (如果有独立的菜单配置文件) (15分钟)

**预计时间**: 30分钟

---

## 🐳 第五阶段：Docker 配置（第 5 周）

### 任务 5.1: 更新 docker-compose.yml

**文件**: `docker-compose.yml`

**实施步骤**:

1. **备份原文件** (5分钟)
   ```bash
   cp docker-compose.yml docker-compose.yml.backup
   ```

2. **修改 volumes 配置** (30分钟)

   添加挂载点映射:
   ```yaml
   volumes:
     # ===== 下载挂载点（预留 4 个）=====
     - ${DOWNLOAD_MOUNT_1_HOST:-./data/downloads/mount_1}:/app/data/downloads/mount_1
     - ${DOWNLOAD_MOUNT_2_HOST:-./data/downloads/mount_2}:/app/data/downloads/mount_2
     - ${DOWNLOAD_MOUNT_3_HOST:-./data/downloads/mount_3}:/app/data/downloads/mount_3
     - ${DOWNLOAD_MOUNT_4_HOST:-./data/downloads/mount_4}:/app/data/downloads/mount_4

     # ===== 媒体库挂载点（预留 10 个）=====
     - ${LIBRARY_MOUNT_1_HOST:-./data/library/mount_1}:/app/data/library/mount_1
     - ${LIBRARY_MOUNT_2_HOST:-./data/library/mount_2}:/app/data/library/mount_2
     - ${LIBRARY_MOUNT_3_HOST:-./data/library/mount_3}:/app/data/library/mount_3
     - ${LIBRARY_MOUNT_4_HOST:-./data/library/mount_4}:/app/data/library/mount_4
     - ${LIBRARY_MOUNT_5_HOST:-./data/library/mount_5}:/app/data/library/mount_5
     - ${LIBRARY_MOUNT_6_HOST:-./data/library/mount_6}:/app/data/library/mount_6
     - ${LIBRARY_MOUNT_7_HOST:-./data/library/mount_7}:/app/data/library/mount_7
     - ${LIBRARY_MOUNT_8_HOST:-./data/library/mount_8}:/app/data/library/mount_8
     - ${LIBRARY_MOUNT_9_HOST:-./data/library/mount_9}:/app/data/library/mount_9
     - ${LIBRARY_MOUNT_10_HOST:-./data/library/mount_10}:/app/data/library/mount_10
   ```

3. **添加 environment 配置** (30分钟)
   ```yaml
   environment:
     # ===== 宿主机路径环境变量（供后端读取并存入数据库）=====
     # 下载挂载点
     DOWNLOAD_MOUNT_1_HOST: ${DOWNLOAD_MOUNT_1_HOST:-}
     DOWNLOAD_MOUNT_2_HOST: ${DOWNLOAD_MOUNT_2_HOST:-}
     DOWNLOAD_MOUNT_3_HOST: ${DOWNLOAD_MOUNT_3_HOST:-}
     DOWNLOAD_MOUNT_4_HOST: ${DOWNLOAD_MOUNT_4_HOST:-}

     # 媒体库挂载点
     LIBRARY_MOUNT_1_HOST: ${LIBRARY_MOUNT_1_HOST:-}
     LIBRARY_MOUNT_2_HOST: ${LIBRARY_MOUNT_2_HOST:-}
     LIBRARY_MOUNT_3_HOST: ${LIBRARY_MOUNT_3_HOST:-}
     LIBRARY_MOUNT_4_HOST: ${LIBRARY_MOUNT_4_HOST:-}
     LIBRARY_MOUNT_5_HOST: ${LIBRARY_MOUNT_5_HOST:-}
     LIBRARY_MOUNT_6_HOST: ${LIBRARY_MOUNT_6_HOST:-}
     LIBRARY_MOUNT_7_HOST: ${LIBRARY_MOUNT_7_HOST:-}
     LIBRARY_MOUNT_8_HOST: ${LIBRARY_MOUNT_8_HOST:-}
     LIBRARY_MOUNT_9_HOST: ${LIBRARY_MOUNT_9_HOST:-}
     LIBRARY_MOUNT_10_HOST: ${LIBRARY_MOUNT_10_HOST:-}
   ```

4. **验证配置** (15分钟)
   ```bash
   # 验证 YAML 语法
   docker-compose config
   ```

**预计时间**: 1.5小时

---

### 任务 5.2: 更新 .env.example

**文件**: `.env.example`

**实施步骤**:

1. **添加新配置** (30分钟)
   ```bash
   # ==============================================================================
   # NasFusion 存储挂载点配置
   # ==============================================================================
   #
   # 说明：
   # 1. 挂载点命名采用 {MOUNT_TYPE}_MOUNT_{N}_HOST 格式
   # 2. 宿主机路径将显示在 Web UI 中，并用于跨系统数据分析
   # 3. 未配置的挂载点使用默认值（./data/downloads 或 ./data/library）
   # 4. 用户可在 Web UI 中编辑宿主机路径
   #
   # ==============================================================================

   # ===== 下载挂载点（按需配置，最多 4 个）=====
   DOWNLOAD_MOUNT_1_HOST=/volume2/Download
   DOWNLOAD_MOUNT_2_HOST=/volume3/Download
   DOWNLOAD_MOUNT_3_HOST=/volume4/WD-Download
   # DOWNLOAD_MOUNT_4_HOST=

   # ===== 媒体库挂载点（按需配置，最多 10 个）=====
   LIBRARY_MOUNT_1_HOST=/volume2/TV
   LIBRARY_MOUNT_2_HOST=/volume2/music
   LIBRARY_MOUNT_3_HOST=/volume2/Movie
   LIBRARY_MOUNT_4_HOST=/volume3/DT-Xvideo
   LIBRARY_MOUNT_5_HOST=/volume4/WD-Books
   LIBRARY_MOUNT_6_HOST=/volume4/WD-HDD
   LIBRARY_MOUNT_7_HOST=/volume4/WD-Music
   LIBRARY_MOUNT_8_HOST=/volume4/WD-TV
   LIBRARY_MOUNT_9_HOST=/volume4/WD-Xvideo/国产
   LIBRARY_MOUNT_10_HOST=/volume4/WD-Xvideo/流出V2

   # ==============================================================================
   # 注意事项：
   # 1. 挂载点编号必须连续（从 1 开始）
   # 2. 路径必须是宿主机的绝对路径
   # 3. 确保路径存在且 Docker 有访问权限
   # 4. 启动后在 Web UI 中配置每个媒体库挂载点的分类（movie/tv/music 等）
   # ==============================================================================
   ```

**预计时间**: 1小时

---

### 任务 5.3: 测试 Docker 部署

**实施步骤**:

1. **创建测试环境** (30分钟)
   ```bash
   # 复制配置文件
   cp .env.example .env

   # 创建测试目录
   mkdir -p /tmp/nasfusion-test/volume2/Download
   mkdir -p /tmp/nasfusion-test/volume2/TV
   mkdir -p /tmp/nasfusion-test/volume2/Movie
   ```

2. **构建和启动** (1小时)
   ```bash
   # 构建镜像
   docker-compose build backend

   # 启动服务
   docker-compose up -d

   # 查看日志
   docker-compose logs -f backend
   ```

3. **验证挂载点扫描** (30分钟)
   ```bash
   # 查看后端日志，确认挂载点扫描成功
   docker-compose logs backend | grep "扫描存储挂载点"

   # 访问 API 验证
   curl http://localhost:8000/api/v1/storage-mounts
   ```

4. **Web UI 测试** (1小时)
   - 访问 http://localhost:5173/storage-mounts
   - 验证挂载点列表显示正常
   - 测试编辑宿主机路径
   - 测试配置媒体分类
   - 测试刷新磁盘信息

**预计时间**: 3小时

---

## ✅ 第六阶段：测试与文档（第 6 周）

### 任务 6.1: 编写单元测试

**实施步骤**:

1. **后端单元测试** (4小时)

   **文件**: `backend/tests/services/test_storage_mount_service.py`
   ```python
   import pytest
   from pathlib import Path
   from app.services.storage.storage_mount_service import StorageMountService

   @pytest.mark.asyncio
   async def test_scan_and_init_mounts(db_session):
       """测试挂载点扫描"""
       # 创建测试目录
       test_download_dir = Path("/tmp/test/downloads/mount_1")
       test_download_dir.mkdir(parents=True, exist_ok=True)

       # 执行扫描
       count = await StorageMountService.scan_and_init_mounts(db_session)

       # 验证结果
       assert count > 0

   @pytest.mark.asyncio
   async def test_get_download_mounts_for_media(db_session):
       """测试获取推荐下载挂载点"""
       mounts = await StorageMountService.get_download_mounts_for_media(
           db_session,
           media_category="movie"
       )

       # 验证同盘优先排序
       assert len(mounts) > 0

   def test_check_same_disk():
       """测试同盘检测"""
       result = StorageMountService.check_same_disk("/tmp/a", "/tmp/b")
       assert "same_disk" in result
       assert "can_hardlink" in result
   ```

2. **前端单元测试** (3小时)

   **文件**: `frontend/tests/views/StorageMounts.spec.ts`
   ```typescript
   import { describe, it, expect, vi } from 'vitest'
   import { mount } from '@vue/test-utils'
   import StorageMounts from '@/views/StorageMounts.vue'

   describe('StorageMounts.vue', () => {
     it('renders mount list correctly', () => {
       const wrapper = mount(StorageMounts)
       expect(wrapper.find('.storage-mounts-page').exists()).toBe(true)
     })

     it('groups mounts by device correctly', async () => {
       // 测试按设备分组逻辑
     })
   })
   ```

**预计时间**: 7小时

---

### 任务 6.2: 编写集成测试

**实施步骤**:

1. **API 集成测试** (4小时)

   **文件**: `backend/tests/integration/test_storage_mounts_api.py`
   ```python
   import pytest
   from httpx import AsyncClient

   @pytest.mark.asyncio
   async def test_storage_mounts_workflow(client: AsyncClient):
       """测试完整工作流"""

       # 1. 扫描挂载点
       scan_res = await client.post("/api/v1/storage-mounts/scan")
       assert scan_res.status_code == 200

       # 2. 获取挂载点列表
       list_res = await client.get("/api/v1/storage-mounts")
       assert list_res.status_code == 200
       mounts = list_res.json()["items"]
       assert len(mounts) > 0

       # 3. 更新挂载点配置
       mount_id = mounts[0]["id"]
       update_res = await client.patch(
           f"/api/v1/storage-mounts/{mount_id}",
           json={"media_category": "movie", "priority": 100}
       )
       assert update_res.status_code == 200

       # 4. 获取推荐下载挂载点
       download_mounts_res = await client.get(
           "/api/v1/storage-mounts/download-mounts",
           params={"media_category": "movie"}
       )
       assert download_mounts_res.status_code == 200

       # 5. 检查同盘
       same_disk_res = await client.post(
           "/api/v1/storage-mounts/check-same-disk",
           json={"path1": "/tmp/a", "path2": "/tmp/b"}
       )
       assert same_disk_res.status_code == 200
   ```

2. **E2E 测试** (可选) (4小时)

   使用 Playwright 或 Cypress 测试完整用户流程

**预计时间**: 8小时

---

### 任务 6.3: 编写用户文档

**实施步骤**:

1. **快速开始指南** (2小时)

   **文件**: `docs/storage_mounts_quick_start.md`
   ```markdown
   # 存储挂载点系统 - 快速开始

   ## 什么是挂载点系统？

   挂载点系统允许您灵活配置多个下载目录和媒体库目录，支持多盘聚合和硬链接优化。

   ## Docker 部署配置

   ### 1. 编辑 .env 文件

   ...（详细步骤）
   ```

2. **配置指南** (3小时)

   **文件**: `docs/storage_mounts_configuration.md`
   - Docker 配置详解
   - 本地部署配置
   - 媒体分类配置
   - 优先级设置
   - 同盘优化说明

3. **故障排查** (2小时)

   **文件**: `docs/storage_mounts_troubleshooting.md`
   - 常见问题
   - 挂载点扫描失败
   - 路径权限问题
   - 同盘检测不准确

4. **更新 CLAUDE.md** (1小时)

   添加存储挂载点系统章节

**预计时间**: 8小时

---

### 任务 6.4: 代码审查和优化

**实施步骤**:

1. **代码审查清单** (2小时)
   - [ ] 所有代码符合命名规范
   - [ ] 所有函数有类型注解
   - [ ] 所有公共方法有文档字符串
   - [ ] 异常处理完善
   - [ ] 日志记录充分
   - [ ] 无安全隐患

2. **性能优化** (3小时)
   - 检查 N+1 查询问题
   - 添加必要的索引
   - 优化大批量操作
   - 前端列表虚拟滚动（如果需要）

3. **UI/UX 改进** (2小时)
   - 加载状态优化
   - 错误提示友好化
   - 添加操作确认对话框
   - 响应式布局调整

**预计时间**: 7小时

---

## 📊 总体时间估算

| 阶段 | 主要任务 | 预计时间 |
|------|---------|---------|
| 第 1 周 | 数据库设计 | 6.5 小时 |
| 第 2 周 | 后端服务层 | 12.5 小时 |
| 第 3 周 | API 接口 | 12.5 小时 |
| 第 4 周 | 前端 UI | 16.5 小时 |
| 第 5 周 | Docker 配置 | 5.5 小时 |
| 第 6 周 | 测试与文档 | 30 小时 |
| **总计** | | **83.5 小时** |

> 约 2 周全职工作量 (按每周 40 小时计算)

---

## ✅ 验收标准

### 功能验收

- [ ] 系统启动时自动扫描并创建挂载点记录
- [ ] Web UI 可以查看所有挂载点信息
- [ ] 可以编辑挂载点的宿主机路径
- [ ] 可以配置媒体库挂载点的分类和优先级
- [ ] 下载任务自动选择推荐的下载挂载点（同盘优先）
- [ ] 整理功能优先使用同盘目标（硬链接）
- [ ] 磁盘空间信息正确显示
- [ ] 同盘检测功能正常工作

### 性能验收

- [ ] 挂载点扫描在 5 秒内完成（最多 14 个挂载点）
- [ ] API 响应时间 < 200ms
- [ ] 前端列表渲染流畅（无明显卡顿）
- [ ] 磁盘信息刷新 < 1 秒

### 兼容性验收

- [ ] Docker 部署成功
- [ ] 本地部署成功（如果实现）
- [ ] 支持 PostgreSQL 数据库
- [ ] 支持 SQLite 数据库（开发环境）
- [ ] 前端在 Chrome、Firefox、Edge 浏览器正常工作

### 文档验收

- [ ] 快速开始指南完整
- [ ] 配置指南详细
- [ ] 故障排查文档有用
- [ ] CLAUDE.md 更新正确
- [ ] API 文档自动生成正确

---

## 🚀 实施建议

### 开发优先级

1. **必须先完成**:
   - 阶段 1（数据库）
   - 阶段 2（后端服务核心方法）

2. **可以并行**:
   - 阶段 3（API）+ 阶段 4（前端 API 客户端）
   - 前端 UI 开发 + 后端集成测试

3. **最后完成**:
   - Docker 配置
   - 文档编写

### 风险控制

1. **技术风险**:
   - 同盘检测在 Docker 环境中可能不准确
   - 缓解：提供手动编辑和验证工具

2. **进度风险**:
   - 前端 UI 工作量可能超出预期
   - 缓解：先实现核心功能，再优化 UI

3. **兼容性风险**:
   - 不同 NAS 系统设备号可能不一致
   - 缓解：充分测试，提供故障排查文档

### 测试策略

1. **单元测试优先**:
   - 每个方法编写完成后立即测试
   - 使用 pytest fixture 准备测试数据

2. **集成测试关键路径**:
   - 重点测试下载路径选择
   - 重点测试整理目标选择

3. **手动测试真实场景**:
   - 在真实 NAS 环境测试
   - 测试多盘场景
   - 测试硬链接功能

---

## 📝 附录：关键代码片段索引

参考实施计划文档中的代码段：

- **StorageMount 模型**: 任务 1.1
- **scan_and_init_mounts()**: 任务 2.1.1
- **get_download_mounts_for_media()**: 任务 2.1.2
- **check_same_disk()**: 任务 2.1.3
- **API 端点**: 任务 3.2
- **前端挂载点列表**: 任务 4.2
- **下载对话框改造**: 任务 4.3
- **docker-compose.yml**: 任务 5.1

---

**文档版本**: v1.1
**创建日期**: 2025-01-03
**最后更新**: 2025-01-03
**维护者**: NasFusion 开发团队
