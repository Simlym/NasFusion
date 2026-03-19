# 存储挂载点系统迁移 - 代码清理总结

## 清理时间
2026-01-03

## 清理原则
由于项目处于开发阶段，直接删除所有废弃代码和向后兼容逻辑，保持代码整洁。

---

## 已删除的废弃代码

### 1. ✅ 配置字段（config.py）
**删除内容**：
- `MEDIA_ROOT` - 旧的媒体文件根目录
- `DOWNLOAD_PATH` - 旧的下载目录

**保留内容**：
- `DOWNLOAD_MOUNTS_BASE` - 下载挂载点基础目录
- `LIBRARY_MOUNTS_BASE` - 媒体库挂载点基础目录

### 2. ✅ 初始化函数（init.py）
**删除内容**：
- `init_default_media_library_settings()` - 整个函数已删除
- 固定目录创建逻辑（`./data/downloads/Movies`、`./data/media/TV` 等）

**新增内容**：
- 挂载点基础目录创建
- `StorageMountService.scan_and_init_mounts()` 调用

### 3. ✅ 服务层回退逻辑（media_organizer_service.py）
**删除内容**：
```python
# 旧代码（已删除）
if not target_mount:
    logger.warning(f"未找到挂载点，使用配置的 library_root: {config.library_root}")
    target_base = Path(config.library_root)
```

**新逻辑**：
```python
# 新代码（直接抛出异常）
if not target_mount:
    raise ValueError(f"未找到媒体类型 {media_file.media_type} 的可用挂载点，请在存储配置中添加")
```

### 4. ✅ 下载服务回退逻辑（download_task_service.py）
**删除内容**：
```python
# 旧代码（已删除）
if not download_mounts:
    logger.warning(f"未找到下载挂载点，使用默认路径: {settings.DOWNLOAD_PATH}")
    data.save_path = settings.DOWNLOAD_PATH
```

**新逻辑**：
```python
# 新代码（直接抛出异常）
if not download_mounts:
    raise ValueError(f"未找到媒体类型 {pt_resource.category} 的可用下载挂载点，请在存储配置中添加")
```

### 5. ✅ 路径转换兼容逻辑（media_directories.py）
**删除内容**：
- 旧路径格式支持（`data/media/...`）

**保留内容**：
- 仅支持新路径格式（`data/library/mount_1/...`）

### 6. ✅ 废弃的服务方法（downloader_config_service.py）
**删除内容**：
- `get_category_paths()` - 获取分类路径列表
- `get_default_path()` - 获取默认下载路径

这两个方法已被挂载点 API 完全替代。

### 7. ✅ 数据库字段标记（downloader_config.py）
**修改内容**：
```python
# 旧注释
comment="分类路径映射，JSON格式：{...详细示例...}"

# 新注释
comment="[已废弃] 分类路径映射，已由 storage_mounts 表替代，保留仅用于数据迁移"
```

**注意**：字段本身保留，因为数据库中可能还有旧数据，避免迁移时丢失。

### 8. ✅ Pydantic Schema 标记（downloader.py）
**修改内容**：
```python
category_paths: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
    None,
    description="[已废弃] 分类路径映射，已由 storage_mounts 表替代",
    deprecated=True,  # 添加废弃标记
)
```

### 9. ✅ 整理配置占位符（organize_config_service.py）
**修改内容**：
```python
# 旧代码
"library_root": f"./data/media/{library_dir}"

# 新代码
"library_root": f"由挂载点系统动态选择"  # 占位符
```

**说明**：`library_root` 字段保留仅用于 UI 显示，实际整理时由 `StorageMountService` 动态选择。

---

## 保留但标记废弃的内容

### 数据库字段
1. **`downloader_config.category_paths`** - JSON 字段
   - 原因：数据库中可能还有旧数据
   - 处理：添加 `[已废弃]` 注释，标记为 `deprecated=True`

2. **`organize_config.library_root`** - 字符串字段
   - 原因：UI 可能还需要显示（占位符）
   - 处理：修改默认值为 `"由挂载点系统动态选择"`

---

## 核心变更总结

### 行为变更
| 场景 | 旧行为 | 新行为 |
|------|--------|--------|
| 未找到挂载点 | 回退到 `settings.DOWNLOAD_PATH` | 抛出异常 `ValueError` |
| 整理未配置 | 使用 `config.library_root` | 抛出异常 `ValueError` |
| 路径转换 | 支持 `data/media/` 和 `data/library/` | 仅支持 `data/library/` |

### 必需配置
用户现在必须配置：
1. ✅ 至少一个下载挂载点（`mount_type='download'`）
2. ✅ 至少一个媒体库挂载点（`mount_type='library'`）

否则下载和整理功能将无法使用（抛出异常）。

---

## 测试建议

### 异常场景测试
1. **未配置挂载点**：
   ```python
   # 预期：抛出 ValueError
   await DownloadTaskService.create(db, data)  # data.save_path = None
   ```

2. **未配置媒体库挂载点**：
   ```python
   # 预期：抛出 ValueError
   await MediaOrganizerService.organize_media_file(db, media_file)
   ```

### 正常场景测试
1. **自动选择下载挂载点**：
   - 创建挂载点：`mount_type='download', media_category='movie'`
   - 下载任务不指定 `save_path`
   - 预期：自动选择该挂载点

2. **同盘优先整理**：
   - 创建两个媒体库挂载点（不同设备）
   - 下载文件在设备 A
   - 预期：优先选择设备 A 的媒体库挂载点

---

## 数据迁移建议

### 对于现有用户（如果有生产数据）

1. **备份数据库**：
   ```bash
   pg_dump nasfusion > backup.sql
   ```

2. **创建挂载点**：
   - 通过 Web UI 或 API 创建挂载点
   - 映射旧的 `DOWNLOAD_PATH` 和 `MEDIA_ROOT` 到新挂载点

3. **测试验证**：
   - 下载新任务
   - 整理旧文件
   - 检查路径是否正确

4. **清理旧数据**（可选）：
   ```sql
   -- 清空 category_paths 字段
   UPDATE downloader_config SET category_paths = NULL;

   -- 清空 system_settings 中的 category_paths
   DELETE FROM system_settings WHERE key = 'category_paths';
   ```

### 对于新用户

直接使用挂载点系统，无需迁移。

---

## 文件清理统计

| 文件 | 删除行数 | 修改行数 | 状态 |
|------|---------|---------|------|
| `backend/app/core/config.py` | 4 | 2 | ✅ 已清理 |
| `backend/app/core/init.py` | 45 | 15 | ✅ 已清理 |
| `backend/app/services/mediafile/media_organizer_service.py` | 8 | 4 | ✅ 已清理 |
| `backend/app/services/download/download_task_service.py` | 6 | 3 | ✅ 已清理 |
| `backend/app/api/v1/media_directories.py` | 12 | 5 | ✅ 已清理 |
| `backend/app/services/mediafile/organize_config_service.py` | 2 | 4 | ✅ 已清理 |
| `backend/app/services/download/downloader_config_service.py` | 48 | 0 | ✅ 已清理 |
| `backend/app/models/downloader_config.py` | 11 | 3 | ✅ 已标记 |
| `backend/app/schemas/downloader.py` | 7 | 3 | ✅ 已标记 |

**总计**：
- 删除代码：143 行
- 修改代码：39 行
- 净减少：104 行

---

## 下一步工作

### 后端
- ✅ 核心代码清理完成
- ⏳ 添加挂载点必需性验证（系统启动时检查）
- ⏳ 添加挂载点健康检查定时任务

### 前端
- ⏳ 更新 `DownloadDialog.vue` 调用挂载点 API
- ⏳ 添加挂载点管理页面
- ⏳ 添加挂载点配置向导

### 文档
- ✅ 迁移总结文档（本文档）
- ⏳ 用户迁移指南
- ⏳ 挂载点配置教程

---

**文档维护者**: Claude Code
**最后更新**: 2026-01-03
**版本**: v1.0 (Clean)
