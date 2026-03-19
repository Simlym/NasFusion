# 存储挂载点重构 - 代码迁移清单

## 📋 概述

从旧的固定路径配置迁移到新的挂载点（Mount）系统后，需要调整以下代码模块。

---

## ✅ 需要调整的文件清单

### 1. **核心配置文件** (`backend/app/core/config.py`)

**问题**: 仍在使用旧的固定路径配置

**当前代码** (第125-131行):
```python
# 文件路径配置
DATA_DIR: str = Field(default="./data", description="数据根目录")
MEDIA_ROOT: str = Field(default="./data/media", description="媒体文件根目录")
DOWNLOAD_PATH: str = Field(default="./data/downloads", description="下载目录")
TORRENT_PATH: str = Field(default="./data/torrents", description="种子文件目录")
LOG_PATH: str = Field(default="./data/logs", description="日志目录")
IMAGE_CACHE_PATH: str = Field(default="./data/cache/images", description="图片缓存目录")
```

**修改建议**:
```python
# 文件路径配置
DATA_DIR: str = Field(default="./data", description="数据根目录")
# ⚠️ 废弃: MEDIA_ROOT 和 DOWNLOAD_PATH 已由挂载点系统管理
# MEDIA_ROOT: str = Field(default="./data/media", description="媒体文件根目录")
# DOWNLOAD_PATH: str = Field(default="./data/downloads", description="下载目录")

# 挂载点基础路径（仅用于 Docker 模式的默认值）
DOWNLOAD_MOUNTS_BASE: str = Field(default="./data/downloads", description="下载挂载点基础目录")
LIBRARY_MOUNTS_BASE: str = Field(default="./data/library", description="媒体库挂载点基础目录")

TORRENT_PATH: str = Field(default="./data/torrents", description="种子文件目录")
LOG_PATH: str = Field(default="./data/logs", description="日志目录")
IMAGE_CACHE_PATH: str = Field(default="./data/cache/images", description="图片缓存目录")
```

**影响范围**:
- 其他模块通过 `settings.MEDIA_ROOT` 或 `settings.DOWNLOAD_PATH` 引用的代码需要改为从挂载点系统获取

---

### 2. **系统初始化** (`backend/app/core/init.py`)

**问题**: `init_media_library_directories()` 函数仍在创建旧的固定目录结构

**当前代码** (第97-191行):
```python
async def init_media_library_directories(db: AsyncSession):
    """
    初始化媒体库目录结构

    - 创建 ./data/downloads/{category}/ 目录
    - 创建 ./data/media/{library}/ 目录
    - 初始化默认配置到 system_settings 表
    - 创建默认整理配置
    """
    logger.info("正在初始化媒体库目录结构...")

    from app.constants.media import MEDIA_TYPES, MEDIA_TYPE_DIRS
    from app.services.mediafile.organize_config_service import OrganizeConfigService

    # 创建下载目录
    download_path = Path(settings.DOWNLOAD_PATH)
    for media_type in MEDIA_TYPES:
        if media_type in MEDIA_TYPE_DIRS:
            dir_name = MEDIA_TYPE_DIRS[media_type]
            category_path = download_path / dir_name
            try:
                category_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建下载目录: {category_path}")
            except Exception as e:
                logger.error(f"创建下载目录失败 {category_path}: {e}")

    # 创建媒体库目录
    media_path = Path("./data/media")
    for media_type in MEDIA_TYPES:
        if media_type in MEDIA_TYPE_DIRS:
            dir_name = MEDIA_TYPE_DIRS[media_type]
            library_path = media_path / dir_name
            try:
                library_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建媒体库目录: {library_path}")
            except Exception as e:
                logger.error(f"创建媒体库目录失败 {library_path}: {e}")

    # 初始化默认配置
    await init_default_media_library_settings(db)

    # 创建默认整理配置
    logger.info("正在创建默认整理配置...")
    try:
        await OrganizeConfigService.create_default_configs(db)
        logger.info("默认整理配置检查完成")
    except Exception as e:
        logger.error(f"创建默认整理配置失败: {e}")

    logger.info("媒体库目录结构初始化完成")
```

**修改建议**:
```python
async def init_media_library_directories(db: AsyncSession):
    """
    初始化媒体库目录结构（新版挂载点系统）

    - 创建挂载点基础目录
    - 初始化挂载点扫描
    - 创建默认整理配置
    """
    logger.info("正在初始化媒体库挂载点...")

    from app.services.storage.storage_mount_service import StorageMountService
    from app.services.mediafile.organize_config_service import OrganizeConfigService

    # 创建挂载点基础目录（Docker 模式下的默认路径）
    download_mounts_base = Path(settings.DOWNLOAD_MOUNTS_BASE)
    library_mounts_base = Path(settings.LIBRARY_MOUNTS_BASE)

    try:
        download_mounts_base.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建下载挂载点基础目录: {download_mounts_base}")
    except Exception as e:
        logger.error(f"创建下载挂载点基础目录失败: {e}")

    try:
        library_mounts_base.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建媒体库挂载点基础目录: {library_mounts_base}")
    except Exception as e:
        logger.error(f"创建媒体库挂载点基础目录失败: {e}")

    # 扫描并初始化挂载点
    logger.info("正在扫描存储挂载点...")
    try:
        created_count = await StorageMountService.scan_and_init_mounts(db)
        logger.info(f"挂载点扫描完成，新增 {created_count} 个挂载点")
    except Exception as e:
        logger.error(f"挂载点扫描失败: {e}")

    # 不再初始化 category_paths 配置（已废弃）
    # await init_default_media_library_settings(db)

    # 创建默认整理配置
    logger.info("正在创建默认整理配置...")
    try:
        await OrganizeConfigService.create_default_configs(db)
        logger.info("默认整理配置检查完成")
    except Exception as e:
        logger.error(f"创建默认整理配置失败: {e}")

    logger.info("媒体库挂载点初始化完成")
```

**删除的函数**:
- `init_default_media_library_settings()` (第150-194行) - 已废弃，不再需要

**影响范围**:
- 系统首次启动时不再创建固定的 `./data/downloads/{category}` 目录
- 改为扫描挂载点并动态创建

---

### 3. **整理配置服务** (`backend/app/services/mediafile/organize_config_service.py`)

**问题**: `create_default_configs()` 方法仍在使用固定的 `library_root` 路径

**当前代码** (第196-203行):
```python
# 生成完整的配置列表
default_configs = []
for media_type, template in config_templates.items():
    if media_type in MEDIA_TYPE_DIRS:
        library_dir = MEDIA_TYPE_DIRS[media_type]
        config = {
            "media_type": media_type,
            "library_root": f"./data/media/{library_dir}",  # ❌ 固定路径
            **template
        }
        default_configs.append(config)
```

**修改建议**:
```python
# 生成完整的配置列表
default_configs = []
for media_type, template in config_templates.items():
    if media_type in MEDIA_TYPE_DIRS:
        config = {
            "media_type": media_type,
            # ⚠️ library_root 字段已废弃，改为从挂载点系统动态获取
            # 保留字段为空，实际使用时从 storage_mounts 表查询
            "library_root": "",  # 空值，表示使用挂载点系统
            **template
        }
        default_configs.append(config)
```

**或者更好的方案** - 修改 `OrganizeConfig` 模型，添加可选的 `target_mount_id` 字段：
```python
# 在 app/models/organize_config.py 中添加
target_mount_id = Column(Integer, ForeignKey("storage_mounts.id"), nullable=True, comment="目标挂载点ID（可选）")
```

然后修改默认配置生成逻辑：
```python
# 为每种媒体类型创建配置，关联到默认挂载点
for config_data in default_configs:
    # ... 现有逻辑 ...

    # 查找该媒体类型的默认挂载点
    from app.services.storage.storage_mount_service import StorageMountService
    default_mount = await StorageMountService.get_default_library_mount(
        db, config_data["media_type"]
    )

    config = OrganizeConfig(
        name=config_data["name"],
        media_type=config_data["media_type"],
        target_mount_id=default_mount.id if default_mount else None,
        library_root=default_mount.container_path if default_mount else "",
        # ... 其他字段 ...
    )
```

**影响范围**:
- 需要修改整理服务，从挂载点系统获取目标路径

---

### 4. **媒体整理服务** (`backend/app/services/mediafile/media_organizer_service.py`)

**问题**: 整理逻辑仍在使用 `config.library_root`

**查找代码中的使用位置**:
```bash
# 搜索 library_root 的使用
grep -n "library_root" backend/app/services/mediafile/media_organizer_service.py
```

**修改建议**:
在 `_organize_movie()` 和 `_organize_tv()` 方法中，替换路径获取逻辑：

**原代码** (假设在方法内):
```python
# 获取目标目录
target_dir = Path(config.library_root) / parsed_dir
```

**新代码**:
```python
# 从挂载点系统获取目标路径
from app.services.storage.storage_mount_service import StorageMountService

# 优先使用 config 关联的挂载点
if config.target_mount_id:
    target_mount = await db.get(StorageMount, config.target_mount_id)
else:
    # 否则获取该媒体类型的默认挂载点（同盘优先）
    target_mount = await StorageMountService.get_organize_target(
        db,
        media_type=media_file.media_type,
        source_path=media_file.file_path
    )

if not target_mount:
    return {
        "status": "error",
        "message": f"未配置 {media_file.media_type} 类型的媒体库挂载点"
    }

# 检查是否同盘（硬链接优化）
same_disk_check = StorageMountService.check_same_disk(
    media_file.file_path,
    target_mount.container_path
)

if same_disk_check["can_hardlink"]:
    logger.info(f"使用硬链接整理（同盘，设备号: {same_disk_check['device_id_1']}）")
    organize_mode = config.organize_mode  # 保持配置的模式
else:
    logger.warning(f"跨盘整理，强制使用复制模式（设备号: {same_disk_check['device_id_1']} → {same_disk_check['device_id_2']}）")
    organize_mode = "copy"  # 跨盘强制复制

# 使用挂载点路径
target_dir = Path(target_mount.container_path) / parsed_dir
```

**影响范围**:
- `_organize_movie()` 方法
- `_organize_tv()` 方法
- 可能的其他整理方法

---

### 5. **媒体目录 API** (`backend/app/api/v1/media_directories.py`)

**问题**: 路径转换函数使用硬编码的 `data/media/`

**当前代码** (第28-54行):
```python
def convert_file_path_to_url(file_path: Optional[str]) -> Optional[str]:
    """
    将文件系统路径转换为HTTP可访问的URL路径

    例如:
        data\\media\\TV Shows\\poster.jpg -> /media/TV Shows/poster.jpg
        ./data/media/Movies/poster.jpg -> /media/Movies/poster.jpg
    """
    if not file_path:
        return None

    # 规范化路径（统一使用正斜杠）
    normalized = file_path.replace("\\", "/")

    # 尝试找到 data/media/ 的位置并截取
    if "data/media/" in normalized:  # ❌ 硬编码
        parts = normalized.split("data/media/")
        if len(parts) > 1:
             # 取最后一部分，再次确保不以 / 开头
             relative_path = parts[-1].lstrip("/")
             return f"/media/{relative_path}"

    # 后备逻辑：移除可能的 ./ 前缀
    if normalized.startswith("./"):
        normalized = normalized[2:]

    return f"/media/{normalized}"
```

**修改建议**:
```python
def convert_file_path_to_url(file_path: Optional[str]) -> Optional[str]:
    """
    将文件系统路径转换为HTTP可访问的URL路径

    支持新的挂载点系统：
        /app/data/library/mount_1/TV Shows/poster.jpg -> /media/mount_1/TV Shows/poster.jpg
        ./data/library/Movies/poster.jpg -> /media/Movies/poster.jpg
    """
    if not file_path:
        return None

    # 规范化路径（统一使用正斜杠）
    normalized = file_path.replace("\\", "/")

    # 新挂载点系统：优先匹配 data/library/
    if "data/library/" in normalized:
        parts = normalized.split("data/library/")
        if len(parts) > 1:
            relative_path = parts[-1].lstrip("/")
            return f"/media/{relative_path}"

    # 兼容旧路径：data/media/
    if "data/media/" in normalized:
        parts = normalized.split("data/media/")
        if len(parts) > 1:
            relative_path = parts[-1].lstrip("/")
            return f"/media/{relative_path}"

    # Docker 环境：/app/data/library/
    if "/app/data/library/" in normalized:
        parts = normalized.split("/app/data/library/")
        if len(parts) > 1:
            relative_path = parts[-1].lstrip("/")
            return f"/media/{relative_path}"

    # 后备逻辑：移除可能的 ./ 前缀
    if normalized.startswith("./"):
        normalized = normalized[2:]

    return f"/media/{normalized}"
```

**影响范围**:
- 海报、背景图的 URL 转换
- 需要同步更新前端静态文件服务路径

---

### 6. **下载器配置** (`backend/app/models/downloader_config.py`)

**问题**: `category_paths` 字段已废弃，但模型仍保留

**当前代码** (第32-47行):
```python
# 分类路径配置
category_paths = Column(
    JSON,
    nullable=True,
    comment="""分类路径映射，JSON格式：
    {
      "movie": [
        {"path": "/downloads/movies", "is_default": true},
        {"path": "/downloads/movies-4k", "is_default": false}
      ],
      "tv": [
        {"path": "/downloads/tv", "is_default": true}
      ]
    }
    """,
)
```

**修改建议**:
```python
# ⚠️ 已废弃：分类路径配置（改用 storage_mounts 系统）
# 保留字段用于兼容旧数据，新代码不应再使用
category_paths = Column(
    JSON,
    nullable=True,
    comment="已废弃：分类路径映射（请使用 storage_mounts 表）",
)
```

**数据库迁移脚本**:
```python
# backend/alembic/versions/xxxx_deprecate_category_paths.py

def upgrade():
    # 添加注释说明字段已废弃
    op.alter_column(
        'downloader_configs',
        'category_paths',
        comment='已废弃：分类路径映射（请使用 storage_mounts 表）'
    )

def downgrade():
    pass  # 保留字段，仅修改注释
```

**影响范围**:
- 下载任务创建时的路径选择逻辑

---

### 7. **下载任务服务** (`backend/app/services/download/download_task_service.py`)

**问题**: 下载路径选择逻辑可能还在使用 `category_paths`

**需要查找的代码模式**:
```python
# 搜索可能的使用位置
grep -n "category_paths\|DOWNLOAD_PATH" backend/app/services/download/download_task_service.py
```

**修改建议**:
在 `create()` 方法中，替换路径选择逻辑：

**原代码** (假设):
```python
if not data.save_path:
    # 从 downloader_config.category_paths 获取路径
    category_paths = downloader.category_paths.get(resource.category, [])
    if category_paths:
        data.save_path = category_paths[0]["path"]
    else:
        data.save_path = f"{settings.DOWNLOAD_PATH}/{resource.category}"
```

**新代码**:
```python
if not data.save_path:
    # 从挂载点系统获取推荐下载路径
    from app.services.storage.storage_mount_service import StorageMountService

    download_mounts = await StorageMountService.get_download_mounts_for_media(
        db,
        media_category=resource.category,
        library_mount_id=data.target_library_mount_id  # 可选，前端传入
    )

    if not download_mounts:
        raise ValueError(f"未配置 {resource.category} 类型的下载挂载点")

    # 使用推荐的第一个挂载点（同盘优先）
    data.save_path = download_mounts[0].container_path
    logger.info(f"自动选择下载挂载点: {download_mounts[0].name} (设备ID: {download_mounts[0].device_id})")
```

**影响范围**:
- 下载任务创建流程

---

### 8. **前端下载对话框** (`frontend/src/components/download/DownloadDialog.vue`)

**问题**: 路径加载逻辑还在使用旧的 `category_paths` API

**当前代码** (第251-336行):
```typescript
// 加载分类路径（从系统设置中读取）
async function loadCategoryPaths(downloader: DownloaderConfig) {
  if (!props.resource?.category) {
    availablePaths.value = []
    form.save_path = ''
    return
  }

  try {
    // 从系统设置中加载媒体库分类路径配置
    const response = await api.settings.getSetting('media_library', 'category_paths')
    // ...
  }
}
```

**修改建议**:
```typescript
import { getDownloadMountsForMedia } from '@/api/modules/storage'

// 加载下载挂载点（从挂载点系统获取）
async function loadCategoryPaths(downloader: DownloaderConfig) {
  if (!props.resource?.category) {
    availablePaths.value = []
    form.save_path = ''
    return
  }

  try {
    // 从挂载点系统获取推荐下载路径
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

    // 自动选择默认路径（同盘优先）
    const defaultPath = availablePaths.value.find(p => p.is_default && p.is_same_disk)
      || availablePaths.value.find(p => p.is_same_disk)
      || availablePaths.value.find(p => p.is_default)
      || availablePaths.value[0]

    if (defaultPath) {
      form.save_path = defaultPath.path
    }
  } catch (error: any) {
    console.error('加载下载挂载点失败:', error)
    ElMessage.error('加载下载挂载点失败')
  }
}
```

**影响范围**:
- 前端下载对话框 UI

---

## 🔄 迁移步骤建议

### 阶段 1：数据库和服务层（优先）
1. ✅ 确认 `storage_mounts` 表已创建
2. ✅ 确认 `StorageMountService` 已实现
3. 🔨 修改 `config.py` - 添加新字段，保留旧字段但标记废弃
4. 🔨 修改 `init.py` - 更新初始化逻辑
5. 🔨 修改 `organize_config_service.py` - 更新默认配置生成

### 阶段 2：整理和下载功能
6. 🔨 修改 `media_organizer_service.py` - 集成挂载点系统
7. 🔨 修改 `download_task_service.py` - 使用新的路径选择逻辑

### 阶段 3：API 层
8. 🔨 修改 `media_directories.py` - 更新路径转换函数
9. 🔨 标记 `category_paths` 字段为废弃

### 阶段 4：前端
10. 🔨 修改 `DownloadDialog.vue` - 使用新的挂载点 API
11. 🔨 测试路径选择和同盘标识显示

### 阶段 5：清理和测试
12. 🧪 全流程测试（扫描 → 识别 → 下载 → 整理）
13. 📝 更新 API 文档
14. 🗑️ （可选）删除废弃字段（需要数据库迁移）

---

## ⚠️ 向后兼容性

为了平滑迁移，建议：

1. **保留旧字段**：暂时保留 `MEDIA_ROOT`、`DOWNLOAD_PATH`、`category_paths` 等字段
2. **双路径支持**：同时支持旧路径和新挂载点，优先使用挂载点
3. **数据迁移脚本**：提供脚本将旧配置迁移到新系统
4. **废弃警告**：在日志中输出废弃警告，提醒用户升级

示例：
```python
# 在 media_organizer_service.py 中
if config.library_root and not config.target_mount_id:
    logger.warning(
        f"配置 '{config.name}' 使用旧的 library_root 字段，"
        f"建议迁移到挂载点系统"
    )
    # 兼容旧逻辑
    target_dir = Path(config.library_root) / parsed_dir
else:
    # 新逻辑：使用挂载点
    target_mount = await StorageMountService.get_organize_target(...)
    target_dir = Path(target_mount.container_path) / parsed_dir
```

---

## 📝 测试清单

迁移完成后，需要测试以下场景：

### 下载流程
- [ ] 创建下载任务时自动选择下载挂载点
- [ ] 下载对话框显示可用挂载点列表
- [ ] 同盘标识正确显示
- [ ] 剩余空间正确显示

### 整理流程
- [ ] 整理时自动选择目标挂载点（同盘优先）
- [ ] 同盘文件使用硬链接
- [ ] 跨盘文件使用复制模式
- [ ] 整理后文件路径正确

### 媒体库扫描
- [ ] 扫描挂载点目录正常工作
- [ ] 海报、背景图 URL 转换正确
- [ ] 目录树显示正常

### 挂载点管理
- [ ] 系统启动时自动扫描挂载点
- [ ] Web UI 可以查看和配置挂载点
- [ ] 磁盘空间信息正确显示

---

**文档版本**: v1.0
**创建日期**: 2025-01-03
**维护者**: NasFusion 开发团队
