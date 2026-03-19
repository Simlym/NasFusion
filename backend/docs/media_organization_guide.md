# 媒体组织功能完整指南

## 📚 目录

1. [功能概述](#功能概述)
2. [核心组件](#核心组件)
3. [快速开始](#快速开始)
4. [使用指南](#使用指南)
5. [API参考](#api参考)
6. [配置说明](#配置说明)
7. [高级用法](#高级用法)
8. [故障排查](#故障排查)

---

## 功能概述

**媒体组织功能**实现了从下载完成到媒体库集成的全生命周期管理，主要包括：

### ✨ 核心特性

- **文件发现**：自动扫描下载目录，发现媒体文件
- **技术信息提取**：使用MediaInfo提取视频编码、分辨率、音轨等信息
- **智能识别**：关联PT资源和统一资源（电影/电视剧）
- **灵活整理**：支持硬链接/软链接/移动/复制四种模式
- **NFO生成**：生成Jellyfin/Emby兼容的NFO文件
- **可配置模板**：自定义目录结构和文件命名规则
- **批量操作**：支持批量整理和dry_run模拟运行

### 🎯 适用场景

- PT站点下载后自动整理到媒体库
- 已有媒体文件的批量整理和重命名
- 多媒体库管理（电影/电视剧分开存放）
- Jellyfin/Emby媒体服务器集成

---

## 核心组件

### 数据模型

#### 1. MediaFile（媒体文件）
管理磁盘上的所有媒体文件及其处理状态。

```python
# 文件基础信息
file_path: str          # 完整路径（唯一）
file_name: str          # 文件名
file_size: int          # 文件大小（字节）
file_type: str          # video/audio/subtitle/other

# 媒体关联
media_type: str         # movie/tv/music/book/anime/adult/unknown
unified_resource_id: int  # 统一资源ID
download_task_id: int   # 下载任务ID

# 处理状态
status: str            # discovered/identifying/identified/organizing/scraping/completed/failed/ignored
organized: bool        # 是否已整理
organized_path: str    # 整理后路径

# 技术信息（从MediaInfo提取）
resolution: str        # 2160p/1080p/720p/480p
codec_video: str       # H.265/H.264/AV1
codec_audio: str       # AAC/DTS/TrueHD
duration: int          # 时长（秒）
```

**文件生命周期**：
```
discovered → identifying → identified → organizing → scraping → completed
    ↓             ↓            ↓            ↓           ↓          ↓
  发现文件      识别中       已识别      整理中      刮削中     已完成
```

#### 2. OrganizeConfig（整理配置）
存储用户自定义的文件整理规则。

```python
name: str                    # 配置名称（唯一）
media_type: str              # movie/tv/music/book/anime/adult
library_root: str            # 媒体库根目录
dir_template: str            # 目录结构模板
filename_template: str       # 文件名模板
organize_mode: str           # hardlink/symlink/move/copy
generate_nfo: bool           # 是否生成NFO
nfo_format: str              # jellyfin/emby/plex/kodi
```

### 服务层

#### 1. MediaFileService
- 文件CRUD操作
- 目录扫描和文件发现
- 关联统一资源

#### 2. MediaInfoService
- 提取视频技术信息
- 更新MediaFile字段

#### 3. OrganizeConfigService
- 配置CRUD操作
- 模板解析

#### 4. MediaOrganizerService（核心）
- 文件整理核心逻辑
- 支持电影和电视剧
- 批量操作

#### 5. NFOGeneratorService
- 生成Jellyfin/Emby NFO
- 下载海报和背景图

---

## 快速开始

### 1. 初始化默认配置

```bash
POST /api/v1/organize-configs/init-defaults
```

这将创建3个默认配置：
- **电影库-默认**：`/media/Movies`
- **电视剧库-默认**：`/media/TV Shows`
- **动漫库-默认**：`/media/Anime`

### 2. 扫描目录

```bash
POST /api/v1/media-files/scan
{
  "directory": "/downloads/completed",
  "recursive": true,
  "media_type": "movie"
}
```

### 3. 提取MediaInfo

```bash
POST /api/v1/media-files/{file_id}/extract-mediainfo
```

### 4. 整理文件

```bash
POST /api/v1/media-files/{file_id}/organize
{
  "config_id": 1,
  "dry_run": false
}
```

---

## 使用指南

### 场景1：下载完成后自动整理

#### 工作流程
```
下载完成 → 创建MediaFile → 提取MediaInfo → 自动整理 → 生成NFO
```

#### 示例代码
```python
from app.services.media_file_service import MediaFileService
from app.services.media_info_service import MediaInfoService
from app.services.media_organizer_service import MediaOrganizerService

# 1. 从下载任务创建媒体文件
media_files = await MediaFileService.create_from_download_task(db, download_task)

# 2. 提取技术信息
for media_file in media_files:
    await MediaInfoService.extract_and_update(db, media_file)

# 3. 整理文件
for media_file in media_files:
    result = await MediaOrganizerService.organize_media_file(
        db, media_file, config=None, dry_run=False
    )
    print(result)
```

### 场景2：批量整理已有文件

#### 步骤

**1. 扫描目录**
```bash
curl -X POST "http://localhost:8000/api/v1/media-files/scan" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/downloads/movies",
    "recursive": true,
    "media_type": "movie"
  }'
```

**2. 批量整理**
```bash
curl -X POST "http://localhost:8000/api/v1/media-files/organize" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_ids": [1, 2, 3, 4, 5],
    "config_id": 1,
    "dry_run": false
  }'
```

### 场景3：自定义配置

#### 创建配置
```bash
curl -X POST "http://localhost:8000/api/v1/organize-configs" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "4K电影库",
    "media_type": "movie",
    "library_root": "/media/Movies-4K",
    "dir_template": "{title} ({year}) [{resolution}]",
    "filename_template": "{title} ({year}) [{resolution}]",
    "organize_mode": "hardlink",
    "generate_nfo": true,
    "nfo_format": "jellyfin"
  }'
```

---

## API参考

### MediaFiles API

#### GET /api/v1/media-files
查询媒体文件列表

**Query参数：**
- `skip`: int - 跳过数量（默认0）
- `limit`: int - 返回数量（默认100）
- `status`: str - 状态过滤
- `media_type`: str - 媒体类型过滤
- `organized`: bool - 是否已整理
- `download_task_id`: int - 下载任务ID

#### GET /api/v1/media-files/{file_id}
获取媒体文件详情

#### POST /api/v1/media-files/scan
扫描目录

**Request Body：**
```json
{
  "directory": "/downloads/completed",
  "recursive": true,
  "media_type": "movie"
}
```

#### POST /api/v1/media-files/{file_id}/extract-mediainfo
提取MediaInfo

#### POST /api/v1/media-files/organize
批量整理

**Request Body：**
```json
{
  "file_ids": [1, 2, 3],
  "config_id": 1,
  "dry_run": false
}
```

#### POST /api/v1/media-files/{file_id}/organize
整理单个文件

**Query参数：**
- `config_id`: int - 配置ID（可选）
- `dry_run`: bool - 是否模拟运行

#### DELETE /api/v1/media-files/{file_id}
删除媒体文件记录

**Query参数：**
- `delete_physical_file`: bool - 是否删除物理文件

### OrganizeConfigs API

#### GET /api/v1/organize-configs
查询配置列表

#### GET /api/v1/organize-configs/{config_id}
获取配置详情

#### GET /api/v1/organize-configs/default/{media_type}
获取默认配置

#### POST /api/v1/organize-configs
创建配置

#### POST /api/v1/organize-configs/init-defaults
初始化默认配置

#### PATCH /api/v1/organize-configs/{config_id}
更新配置

#### DELETE /api/v1/organize-configs/{config_id}
删除配置

---

## 配置说明

### 目录结构模板

#### 电影模板

**默认模板：**
```
dir_template: "{title} ({year})"
filename_template: "{title} ({year})"
```

**示例输出：**
```
/media/Movies/
├── 肖申克的救赎 (1994)/
│   ├── 肖申克的救赎 (1994).mkv
│   ├── 肖申克的救赎 (1994).nfo
│   ├── poster.jpg
│   └── backdrop.jpg
```

**支持的变量：**
- `{title}`: 电影标题
- `{original_title}`: 原始标题
- `{year}`: 年份
- `{resolution}`: 分辨率（2160p/1080p等）
- `{quality}`: 质量（同resolution）

#### 电视剧模板

**默认模板：**
```
dir_template: "{title}/Season {season:02d}"
filename_template: "{title} S{season:02d}E{episode:02d}"
```

**示例输出：**
```
/media/TV Shows/
├── 权力的游戏/
│   ├── Season 01/
│   │   ├── 权力的游戏 S01E01.mkv
│   │   ├── 权力的游戏 S01E02.mkv
│   │   └── ...
│   ├── Season 02/
│   │   └── ...
```

**支持的变量：**
- `{title}`: 剧集标题
- `{original_title}`: 原始标题
- `{year}`: 年份
- `{season}`: 季数
- `{season:02d}`: 季数（补零，如01）
- `{episode}`: 集数
- `{episode:02d}`: 集数（补零，如01）
- `{episode_title}`: 集标题
- `{resolution}`: 分辨率

### 整理模式

#### hardlink（硬链接，推荐）
- **优点**：节省空间，不影响做种
- **原理**：创建指向同一inode的新文件名
- **限制**：必须在同一文件系统，不支持目录

#### reflink（Reflink/CoW克隆，Btrfs推荐）
- **优点**：节省空间，可跨共享目录（同一Btrfs卷），独立文件
- **原理**：使用Copy-on-Write技术创建文件克隆，只有修改时才实际复制数据
- **限制**：需要支持CoW的文件系统（如Btrfs、XFS等）
- **适用场景**：群晖NAS等使用Btrfs文件系统的环境

#### symlink（软链接）
- **优点**：可跨文件系统
- **缺点**：某些媒体服务器可能不识别

#### move（移动）
- **优点**：文件只存在一份
- **缺点**：影响做种

#### copy（复制）
- **优点**：源文件不受影响
- **缺点**：占用双倍空间

---

## 高级用法

### dry_run模拟运行

在实际整理前，使用`dry_run=true`预览结果：

```python
result = await MediaOrganizerService.organize_media_file(
    db, media_file, config, dry_run=True
)
print(f"预期路径: {result['organized_path']}")
print(f"整理模式: {result['organize_mode']}")
```

### 自定义文件名清理

使用`sanitize_filename`函数清理非法字符：

```python
from app.utils.file_operations import sanitize_filename

clean_name = sanitize_filename("电影名称:特殊/字符?")
# 输出: "电影名称_特殊_字符_"
```

### MediaInfo提取

```python
from app.utils.mediainfo_parser import parse_media_file, extract_simplified_info

# 完整解析
parsed = parse_media_file("/path/to/video.mkv")

# 提取简化信息
simplified = extract_simplified_info(parsed)
print(f"分辨率: {simplified['resolution']}")
print(f"视频编码: {simplified['codec_video']}")
print(f"时长: {simplified['duration']}秒")
```

---

## 故障排查

### 问题1：MediaInfo提取失败

**症状：**提示`pymediainfo库未安装`

**解决方法：**
```bash
pip install pymediainfo
```

如果是Linux，还需要安装系统库：
```bash
# Ubuntu/Debian
sudo apt-get install libmediainfo-dev

# CentOS/RHEL
sudo yum install mediainfo-devel
```

### 问题2：硬链接失败

**症状：**提示`Invalid cross-device link`

**原因：**源文件和目标目录不在同一文件系统或跨共享目录（群晖NAS常见问题）

**解决方法：**
1. **推荐**：使用`reflink`模式（适用于Btrfs文件系统，如群晖NAS）
2. 使用`symlink`模式（某些媒体服务器可能不识别软链接）
3. 使用`copy`模式（会占用额外空间）
4. 或将媒体库移到同一分区/共享目录

### 问题3：NFO生成失败

**症状：**NFO文件为空或格式错误

**原因：**统一资源元数据不完整

**解决方法：**
1. 检查UnifiedMovie/UnifiedTVSeries数据完整性
2. 重新获取元数据

### 问题4：文件名包含非法字符

**症状：**整理失败，提示文件名非法

**原因：**标题包含`<>:"/\|?*`等字符

**解决方法：**
- 系统会自动调用`sanitize_filename`清理
- 如需自定义，修改`file_operations.py`

---

## 最佳实践

### 1. 推荐配置

**电影库：**
```json
{
  "organize_mode": "hardlink",
  "generate_nfo": true,
  "download_poster": true,
  "skip_existed": true
}
```

**电视剧库：**
```json
{
  "organize_mode": "hardlink",
  "generate_nfo": true,
  "organize_subtitles": true
}
```

### 2. 自动化工作流

**方案1：下载完成后触发**
```python
# 在DownloadTask状态变为completed时
if task.status == "completed" and task.auto_organize:
    media_files = await MediaFileService.create_from_download_task(db, task)
    for media_file in media_files:
        await MediaInfoService.extract_and_update(db, media_file)
        await MediaOrganizerService.organize_media_file(db, media_file)
```

**方案2：定时扫描**
```python
# 使用APScheduler定时扫描
@scheduler.scheduled_job('interval', hours=1)
async def scan_and_organize():
    media_files = await MediaFileService.scan_directory(db, "/downloads")
    # ... 批量处理
```

### 3. 监控和日志

- 查看`backend/logs/app.log`了解处理进度
- 使用`MediaFile.error_message`排查失败原因
- 统计`OrganizeConfig.total_organized_count`了解使用情况

---

## 附录

### 文件扩展名支持

**视频：**
`.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.ts`, `.m2ts`, `.rmvb`, `.iso`

**音频：**
`.mp3`, `.flac`, `.wav`, `.aac`, `.m4a`, `.wma`, `.ogg`, `.ape`, `.alac`, `.dts`, `.ac3`, `.eac3`

**字幕：**
`.srt`, `.ass`, `.ssa`, `.sub`, `.idx`, `.vtt`, `.sup`

### 相关文档

- [数据库设计文档](database/02-core-tables.md)
- [下载管理文档](download_management.md)
- [MTeam集成指南](mteam_integration_guide.md)

---

**文档版本：** 1.0
**最后更新：** 2025-01-12
