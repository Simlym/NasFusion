# NasFusion 媒体库管理与同步逻辑文档

本文档详细说明了 NasFusion 中媒体目录管理、元数据检测以及与媒体服务器（Jellyfin/Emby）关联的核心逻辑。

## 1. 媒体目录服务 (`MediaDirectoryService`)

该服务层负责管理和操作媒体库中的目录结构（`MediaDirectory` 模型），提供从数据库查询到物理文件系统检测的一系列功能。

### 核心功能
*   **目录树构建**：支持按层级（Parent ID）或扁平化问题过滤模式获取目录列表。
*   **元数据实时检测**：通过 `check_metadata_realtime` 方法实时判断目录下是否存在 `.nfo` 信息文件、海报（Poster）和背景图（Backdrop）。
    *   **策略**：优先按标准命名匹配，失败后执行全目录扫描。
*   **问题诊断**：自动识别并标记目录问题（如缺少海报、缺少 NFO、未识别、空文件夹等），并将结果存入 `issue_flags` 字段。
*   **统计分析**：计算特定目录的文件总数、总大小、视频比率等。

---

## 2. 媒体服务器关联逻辑 (`get_directory_detail`)

`get_directory_detail` 方法在获取目录详情时，会动态地将本地文件与媒体服务器中的资源进行“缝合”。

### 关联过程
1.  **查找桥梁记录**：通过 `MediaFile.id` 在 `MediaServerItem` 表中查找对应的激活记录。
2.  **获取服务器配置**：根据关联记录找到对应的 `MediaServerConfig`（获取 IP、端口、SSL 配置）。
3.  **生成 Web URL**：利用服务器地址和 `server_item_id`（媒体服务器内部 ID）构建详情页跳转链接。
    *   **格式**：`{base_url}/web/index.html#!/details?id={server_item_id}`
4.  **前端应用**：前端 UI 接收到 `jellyfin_web_url` 后，会显示“在媒体服务器中打开”的按钮。

---

## 3. 媒体项与本地文件绑定机制 (`MediaServerItem.media_file_id`)

`media_file_id` 是连接 NasFusion 本地管理与外部媒体服务器的核心字段。

### 赋值时机
该字段在执行 **“媒体服务器库同步 (Media Server Library Sync)”** 任务时被自动赋值。

### 详细绑定流程
1.  **数据同步**：从 Jellyfin/Emby 获取原始媒体项并创建/更新本地 `MediaServerItem` 记录。
2.  **路径转换**：
    *   读取 `MediaServerConfig` 中的 **路径映射 (Path Mappings)**。
    *   将媒体服务器返回的路径（如 `/media/movies/Avatar.mp4`）转换为本地 NAS 路径（如 `/volume1/Media/Movies/Avatar.mp4`）。
3.  **路径匹配**：拿着转换后的路径去 `MediaFile` 表中搜索匹配的记录。
4.  **写入关联**：一旦找到匹配的本地文件记录，系统会调用 `update_associations` 将 `media_file_id` 写入 `MediaServerItem`。

### 核心结论
*   **纽带**：绑定完全依赖于 **物理文件路径**（及路径映射配置）。
*   **前提**：必须先运行本地“磁盘扫描”，然后再运行“库同步任务”，两者才能完成握手关联。
