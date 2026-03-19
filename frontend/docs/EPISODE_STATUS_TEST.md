# 集数状态可视化测试指南

## 功能说明

在订阅详情页面 (http://localhost:3000/subscriptions/:id) 中，电视剧订阅会显示集数状态可视化组件。

## 功能特性

### 1. 集数方格展示
- 每集显示为一个方格
- 方格包含：集数、状态图标、质量、进度（如适用）
- 点击方格可查看详细信息

### 2. 状态颜色说明

| 状态 | 颜色 | 边框 | 图标 | 说明 |
|------|------|------|------|------|
| **已下载** (downloaded) | 浅蓝背景 | 绿色边框 | ✓ | 已下载完成并整理 |
| **下载中** (downloading) | 淡蓝背景 | 蓝色边框 | ⟳ (旋转) | 正在下载中 |
| **有资源** (available) | 浅黄背景 | 橙色边框 | ↓ | 找到可用资源，等待下载 |
| **等待中** (waiting) | 灰色背景 | 灰色边框 | ⏱ | 尚未找到资源 |
| **失败** (failed) | 浅红背景 | 红色边框 | ✗ | 下载失败 |

### 3. 统计信息栏
显示各状态的集数统计：
- 已下载：X 集
- 下载中：X 集
- 有资源：X 集
- 等待中：X 集
- 失败：X 集（如有）

### 4. 刷新功能
点击"刷新状态"按钮会：
- 调用后端 API 重新扫描 media_files、download_tasks、pt_resources
- 更新所有集数的最新状态
- 显示刷新成功提示

### 5. 集数详情弹窗
点击任意集数方格会弹出详情对话框，显示：
- 状态标签
- 质量（如 1080p）
- 文件大小
- 文件路径（如已下载）
- 下载进度（如下载中）
- 可用资源数量（如有资源）
- 可用质量列表（如有资源）
- 相关时间戳（下载时间、发现时间等）

## 实现文件

### 后端
- API: `backend/app/api/v1/subscriptions.py`
  - `GET /api/v1/subscriptions/{id}/episodes-status?refresh=false`
  - `POST /api/v1/subscriptions/{id}/episodes-status/refresh`
- Service: `backend/app/services/subscription_episode_service.py`

### 前端
- 组件: `frontend/src/components/subscription/EpisodeStatusGrid.vue`
- 页面: `frontend/src/views/SubscriptionDetail.vue`
- API: `frontend/src/api/modules/subscription.ts`
  - `getEpisodesStatus(id, refresh)`
  - `refreshEpisodesStatus(id)`

## 测试步骤

### 1. 启动服务

```bash
# 后端
cd backend
python -m app.main

# 前端
cd frontend
npm run dev
```

### 2. 创建电视剧订阅

访问 http://localhost:3000 并：
1. 确保有电视剧资源数据（unified_tv_series 表）
2. 创建一个电视剧订阅，设置：
   - 媒体类型：电视剧
   - 订阅季度：第 1 季
   - 总集数：12 集（或实际集数）
   - 自动下载：开启（可选）

### 3. 查看集数状态

访问 http://localhost:3000/subscriptions/{订阅ID}

**预期显示**：
- 订阅信息卡片
- 集数状态卡片（仅电视剧显示）
  - 标题："集数状态 · 第 X 季 · 共 Y 集"
  - 统计信息栏
  - 集数网格（每集一个方格）
- 匹配的PT资源列表
- 检查日志

### 4. 测试集数状态场景

#### 场景 A：全部等待中（初始状态）
- 刚创建订阅，还未检查
- 所有集数显示灰色，状态为"等待中"

#### 场景 B：有可用资源
- 手动触发订阅检查（或等待定时任务）
- 匹配到资源的集数显示黄色，状态为"有资源"
- 点击方格可看到：
  - 可用资源数量
  - 可用质量列表
  - 资源发现时间

#### 场景 C：下载中
- 如果开启了自动下载
- 创建下载任务的集数显示蓝色，状态为"下载中"
- 点击方格可看到：
  - 下载进度百分比
  - 质量信息
  - 开始时间

#### 场景 D：已下载
- 下载完成并整理后
- 集数显示绿色，状态为"已下载"
- 点击方格可看到：
  - 文件大小
  - 文件路径
  - 质量
  - 下载完成时间

### 5. 测试刷新功能

1. 点击"刷新状态"按钮
2. 按钮显示 loading 状态
3. 后端重新扫描所有数据源
4. 前端更新显示最新状态
5. 显示"集数状态已刷新"提示

### 6. 测试详情弹窗

1. 点击任意集数方格
2. 弹出详情对话框
3. 检查显示的信息是否完整
4. 关闭对话框

## API 响应示例

### GET /api/v1/subscriptions/1/episodes-status

```json
{
  "code": 200,
  "data": {
    "subscriptionId": 1,
    "season": 1,
    "startEpisode": 1,
    "totalEpisodes": 12,
    "episodes": {
      "1": {
        "status": "downloaded",
        "file_id": 123,
        "quality": "1080p",
        "file_size": 2147483648,
        "file_path": "/media/tv/Show.S01E01.1080p.mkv",
        "downloaded_at": "2025-11-23T20:00:00+08:00"
      },
      "2": {
        "status": "downloading",
        "task_id": 45,
        "progress": 65,
        "quality": "1080p",
        "started_at": "2025-11-23T21:00:00+08:00"
      },
      "3": {
        "status": "available",
        "resource_ids": [101, 102, 103],
        "qualities": ["1080p", "720p"],
        "best_quality": "1080p",
        "resource_count": 3,
        "found_at": "2025-11-23T22:00:00+08:00"
      },
      "4": {
        "status": "waiting",
        "checked_at": "2025-11-23T22:30:00+08:00"
      }
    },
    "stats": {
      "total": 12,
      "downloaded": 1,
      "downloading": 1,
      "available": 1,
      "waiting": 9,
      "failed": 0
    },
    "last_updated": "2025-11-23T22:30:00+08:00"
  }
}
```

## 常见问题排查

### Q1: 集数状态卡片不显示
**检查**：
- 订阅的 `mediaType` 是否为 `"tv"`（电影订阅不显示）
- 浏览器控制台是否有错误
- API 请求是否成功（Network 标签）

### Q2: 所有集数都是"等待中"
**原因**：
- 订阅还未检查过
- PT 资源的 `tv_info` 字段未正确解析季度/集数
- `resource_mappings` 表未关联到该电视剧

**解决**：
1. 手动触发订阅检查：POST /api/v1/subscriptions/{id}/check
2. 检查 PT 资源的 `tv_info` 字段是否包含正确的季度和集数信息
3. 确认 `resource_mappings` 表有该剧的关联记录

### Q3: 刷新按钮无响应
**检查**：
- 浏览器控制台是否有错误
- API 调用是否返回 401（未登录）
- 后端服务是否正常运行

### Q4: 详情弹窗信息不完整
**原因**：
- 不同状态显示不同字段，这是正常的
- 例如"等待中"状态只有 `checked_at`，没有文件信息

## 样式说明

- 响应式网格布局：根据屏幕宽度自动调整列数
- 方格宽高比 1:1，确保正方形显示
- Hover 效果：悬停时方格上浮并显示阴影
- 下载中动画：图标旋转动画
- 统计栏：彩色左边框标识不同状态

## 后续优化建议

1. **实时更新**：使用 WebSocket 或轮询实现实时状态更新
2. **批量操作**：支持选择多集批量下载
3. **进度条**：为下载中的集数显示进度条
4. **筛选功能**：按状态筛选显示集数
5. **排序选项**：按集数、状态、时间排序
6. **通知提醒**：新集下载完成后浏览器通知

---

**测试完成后**，请确认以下功能是否正常：
- ✅ 集数状态卡片正常显示
- ✅ 状态颜色和图标正确
- ✅ 统计信息准确
- ✅ 刷新功能正常工作
- ✅ 详情弹窗显示正确
- ✅ 响应式布局正常
