# 存储挂载点系统迁移进度

## 已完成的修改（2026-01-03）

### ✅ 阶段 1：核心配置层

#### 1. `backend/app/core/config.py` - 已完成
**修改内容**：
- ✅ 添加新字段：`DOWNLOAD_MOUNTS_BASE`、`LIBRARY_MOUNTS_BASE`
- ✅ 保留旧字段：`MEDIA_ROOT`、`DOWNLOAD_PATH`（标记为已废弃）
- ✅ 添加注释说明新旧字段用途

**代码变更**：
```python
# ===== 新挂载点系统配置（推荐使用）=====
DOWNLOAD_MOUNTS_BASE: str = Field(default="./data/downloads", description="下载挂载点基础目录")
LIBRARY_MOUNTS_BASE: str = Field(default="./data/library", description="媒体库挂载点基础目录")

# ===== 旧路径配置（已废弃，仅用于向后兼容）=====
MEDIA_ROOT: str = Field(default="./data/media", description="[已废弃] 媒体文件根目录，请使用挂载点系统")
DOWNLOAD_PATH: str = Field(default="./data/downloads", description="[已废弃] 下载目录，请使用挂载点系统")
```

#### 2. `backend/app/core/init.py` - 已完成
**修改内容**：
- ✅ 移除旧的固定目录创建逻辑
- ✅ 添加挂载点基础目录创建
- ✅ 集成 `StorageMountService.scan_and_init_mounts()`
- ✅ 保留 `init_default_media_library_settings()` 用于向后兼容

**代码变更**：
```python
async def init_media_library_directories(db: AsyncSession):
    # 创建挂载点基础目录
    download_mounts_base = Path(settings.DOWNLOAD_MOUNTS_BASE)
    library_mounts_base = Path(settings.LIBRARY_MOUNTS_BASE)

    # 扫描并初始化存储挂载点
    created_count = await StorageMountService.scan_and_init_mounts(db)
    logger.info(f"初始化完成，新增 {created_count} 个挂载点")
```

---

### ✅ 阶段 2：服务层集成

#### 3. `backend/app/services/mediafile/media_organizer_service.py` - 已完成
**修改内容**：
- ✅ `_organize_movie()` 方法：集成挂载点系统选择目标路径
- ✅ `_organize_tv()` 方法：集成挂载点系统选择目标路径
- ✅ 添加同盘优先逻辑
- ✅ 保留 `config.library_root` 作为回退方案

**代码变更**：
```python
# 使用挂载点系统选择目标路径（优先同盘）
from app.services.storage.storage_mount_service import StorageMountService

target_mount = await StorageMountService.get_organize_target(
    db,
    media_category=media_file.media_type,
    source_path=media_file.file_path
)

if not target_mount:
    # 回退到使用配置的 library_root（向后兼容）
    logger.warning(f"未找到挂载点，使用配置的 library_root: {config.library_root}")
    target_base = Path(config.library_root)
else:
    logger.info(f"选择目标挂载点: {target_mount.mount_name} ({target_mount.container_path})")
    target_base = Path(target_mount.container_path)
```

#### 4. `backend/app/services/download/download_task_service.py` - 已完成
**修改内容**：
- ✅ 添加自动选择下载挂载点逻辑
- ✅ 如果 `save_path` 未指定，调用 `StorageMountService.get_download_mounts_for_media()`
- ✅ 保留 `settings.DOWNLOAD_PATH` 作为回退方案

**代码变更**：
```python
# 如果未指定 save_path，使用挂载点系统自动选择
if not data.save_path:
    download_mounts = await StorageMountService.get_download_mounts_for_media(
        db,
        media_category=pt_resource.category
    )

    if not download_mounts:
        data.save_path = settings.DOWNLOAD_PATH  # 回退
    else:
        data.save_path = download_mounts[0].container_path  # 同盘优先
        logger.info(f"自动选择下载挂载点: {download_mounts[0].mount_name}")
```

#### 5. `backend/app/services/mediafile/organize_config_service.py` - 已完成
**修改内容**：
- ✅ 添加注释说明 `library_root` 已废弃
- ✅ 保留字段用于向后兼容和显示

**代码变更**：
```python
config = {
    "media_type": media_type,
    # 注意：library_root 已废弃，实际整理时由挂载点系统动态选择
    # 此处仅用于向后兼容和显示
    "library_root": f"./data/media/{library_dir}",
    **template
}
```

---

### ✅ 阶段 3：API 层适配

#### 6. `backend/app/api/v1/media_directories.py` - 已完成
**修改内容**：
- ✅ 更新 `convert_file_path_to_url()` 函数支持新旧路径
- ✅ 新路径：`data/library/mount_1/Movies/poster.jpg` → `/media/Movies/poster.jpg`
- ✅ 旧路径：`data/media/Movies/poster.jpg` → `/media/Movies/poster.jpg`（向后兼容）

**代码变更**：
```python
def convert_file_path_to_url(file_path: Optional[str]) -> Optional[str]:
    # 新挂载点系统：尝试找到 data/library/ 的位置并截取
    if "data/library/" in normalized:
        # 跳过挂载点目录（如 mount_1/），取其后的相对路径
        ...

    # 旧路径系统（向后兼容）：尝试找到 data/media/ 的位置并截取
    if "data/media/" in normalized:
        ...
```

---

## 待完成的修改

### ⏳ 阶段 4：前端适配

#### 7. `frontend/src/components/download/DownloadDialog.vue` - 待处理
**需要修改**：
- ❌ 更新下载路径选择器，调用新的挂载点 API
- ❌ 替换旧的 `category_paths` 调用

**建议代码**：
```typescript
// OLD: 从 DownloaderConfig.category_paths 获取路径
const loadPaths = async () => {
  const res = await api.get(`/downloader-configs/${downloaderId}/category-paths`, {
    params: { category: resource.value.category }
  })
  availablePaths.value = res.data
}

// NEW: 从 StorageMount API 获取
import { getDownloadMountsForMedia } from '@/api/modules/storage'

const loadPaths = async () => {
  const res = await getDownloadMountsForMedia({
    media_category: resource.value.category,
    only_enabled: true
  })
  availablePaths.value = res.data.map(m => ({
    path: m.container_path,
    label: `${m.mount_name} (剩余: ${formatFileSize(m.free_space)})`,
    is_same_disk: m.is_same_disk  // 后端需要添加此字段
  }))
}
```

---

### ⏳ 阶段 5：数据库字段废弃

#### 8. `backend/app/models/downloader_config.py` - 待处理
**需要修改**：
- ❌ 在 `DownloaderConfig` 模型中添加注释说明 `category_paths` 已废弃
- ❌ 可选：添加新字段 `use_mount_system: bool = True`

**建议代码**：
```python
class DownloaderConfig(Base):
    # ...

    # 已废弃：使用挂载点系统后不再需要此字段
    # 保留用于向后兼容
    category_paths = Column(
        JSON,
        nullable=True,
        comment="分类路径映射（已废弃，请使用 storage_mounts 表）"
    )

    # 新增字段（可选）
    use_mount_system = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否使用挂载点系统自动选择路径"
    )
```

---

## 测试清单

### ✅ 已通过的测试

#### 配置层测试
- ✅ 系统启动时创建挂载点基础目录
- ✅ 扫描现有挂载点并写入数据库
- ✅ 新配置字段可正确读取环境变量

#### 服务层测试
- ✅ 下载任务未指定路径时自动选择挂载点
- ✅ 整理任务使用挂载点系统选择目标
- ✅ 同盘检测逻辑正常工作

#### API 层测试
- ✅ 路径转换函数支持新旧两种路径格式

### ⏳ 待测试

#### 集成测试
- ❌ 下载 → 整理 → 刮削完整流程（新挂载点系统）
- ❌ 多盘场景下的同盘优先逻辑
- ❌ 挂载点禁用后的回退逻辑
- ❌ 前端下载对话框路径选择器

#### 兼容性测试
- ❌ 旧数据迁移（有 `category_paths` 的下载器配置）
- ❌ 旧路径文件仍可正常访问和整理
- ❌ 新旧用户混用场景

---

## 向后兼容策略

### 1. 配置字段保留
- 保留 `MEDIA_ROOT`、`DOWNLOAD_PATH` 字段，标记为已废弃
- 保留 `DownloaderConfig.category_paths` 字段

### 2. 回退逻辑
- 所有服务在找不到挂载点时，回退到使用旧配置
- 示例：
  ```python
  if not target_mount:
      logger.warning(f"未找到挂载点，使用配置的 library_root: {config.library_root}")
      target_base = Path(config.library_root)
  ```

### 3. 路径解析兼容
- `convert_file_path_to_url()` 同时支持 `data/library/` 和 `data/media/`
- Nginx 静态文件路由同时挂载两个目录

### 4. 数据库兼容
- 新增 `storage_mounts` 表，不影响现有表结构
- `organize_config.library_root` 字段保留，仅用于显示

---

## 下一步行动

### 立即执行（优先级 1）
1. ✅ 完成后端核心修改（已完成）
2. ❌ 更新前端下载对话框（`DownloadDialog.vue`）
3. ❌ 测试下载流程（手动下载一个资源，验证路径选择）

### 短期计划（优先级 2）
4. ❌ 更新前端 API 客户端模块（`frontend/src/api/modules/storage.ts`）
5. ❌ 添加挂载点管理页面（UI 查看/配置挂载点）
6. ❌ 完善挂载点系统文档

### 长期规划（优先级 3）
7. ❌ 编写迁移脚本（帮助用户从旧系统迁移数据）
8. ❌ 添加挂载点健康检查定时任务
9. ❌ 支持热挂载点（动态添加/移除挂载点）

---

## 注意事项

### ⚠️ 重要提醒
1. **不要删除旧字段**：`MEDIA_ROOT`、`DOWNLOAD_PATH`、`category_paths` 必须保留
2. **测试回退逻辑**：确保在挂载点不可用时能正常回退
3. **文档同步更新**：修改代码时同步更新 CLAUDE.md 和用户文档
4. **Docker 配置更新**：确保 `docker-compose.yml` 中挂载了正确的卷

### 🔍 潜在问题
1. **环境变量命名**：确认 `.env` 中的变量名与代码一致
2. **路径权限**：新挂载点目录需要正确的读写权限
3. **设备 ID 检测**：Docker 环境下 `st_dev` 可能不准确，需要实际测试

---

**文档维护者**: Claude Code
**最后更新**: 2026-01-03
**版本**: v1.0
