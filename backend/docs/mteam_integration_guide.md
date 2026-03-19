# MTeam 站点集成指南

本文档介绍如何在 NasFusion 系统中集成 MTeam 站点，实现 PT 资源的自动同步和管理。

## 概述

本文档主要涵盖以下内容：

### 核心组件
1. **数据模型**
   - `PTResource` - PT资源数据模型，存储同步的资源信息
   - `SyncLog` - 同步日志模型，记录同步过程和结果

2. **MTeam 适配器** (`app/adapters/pt_sites/mteam.py`)
   - 实现 API 接口调用
   - Passkey 认证处理
   - 分页数据获取
   - 资源详情获取
   - 下载链接生成
   - 健康检查
   - 错误处理

3. **服务层** (`app/services/pt_resource_service.py`)
   - 资源 CRUD 操作
   - 站点同步管理
   - 资源去重处理
   - 同步任务调度

4. **API 接口** (`/api/v1/pt-resources`)
   - `GET /pt-resources` - 获取资源列表/搜索过滤
   - `GET /pt-resources/{id}` - 获取资源详情
   - `POST /pt-resources/sites/{site_id}/sync` - 手动同步
   - `GET /pt-resources/sites/{site_id}/sync-logs` - 同步日志
   - `DELETE /pt-resources/{id}` - 删除资源

---

## 技术实现

### MTeam 站点配置

以下配置需要添加到 MTeam 站点配置中：

#### 1. API 基础配置
```
- base_url: MTeam 站点基础 URL，例如：https://kp.m-team.cc
- passkey: 用户 Passkey（在站点控制面板获取）
```

#### 2. API 端点

适配器会使用以下 API 端点：

| 功能 | 端点路径 | 描述 |
|------|----------|------------------|
| 获取资源 | `/api/torrents` | 获取种子列表 |
| 获取详情 | `/api/torrents/{id}` | 获取种子详情 |
| 下载链接 | `/download.php?id={id}&passkey={passkey}` | 生成下载链接 |
| 健康检查 | `/api/health` | 检查站点状态 |

#### 3. API 数据格式

适配器需要处理以下数据格式：

**获取资源 API 响应格式**：
```json
{
  "data": [
    {
      "id": 12345,
      "title": "电影标题",
      "size": 5368709120,
      "seeders": 10,
      // ... 其他字段
    }
  ],
  "total": 1000,
  "page": 1
}
```

**关键字段映射**：
- 资源 ID 字段：`id` 或 `torrent_id`
- 分类字段：`category` 分类标识
- 状态字段：`status` 或 `promotion`
- IMDB/豆瓣 ID 字段

#### 4. 同步策略
```
- request_interval: 请求间隔时间（秒）
- max_requests_per_day: 每日最大请求数量
```

---

## 使用说明

### 1. 添加 MTeam 站点

**API 请求**：
```bash
POST /api/v1/pt-sites
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "name": "MTeam",
  "type": "mteam",
  "domain": "kp.m-team.cc",
  "base_url": "https://kp.m-team.cc",
  "auth_type": "passkey",
  "auth_passkey": "your_passkey_here",
  "sync_enabled": true,
  "sync_strategy": "page_based",
  "sync_interval": 60,
  "request_interval": 2,
  "max_requests_per_day": 1000
}
```

**响应**：
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "MTeam",
    "type": "mteam",
    "status": "active",
    // ... 其他字段
  }
}
```

### 2. 手动同步

**API 请求**：
```bash
POST /api/v1/pt-resources/sites/1/sync
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "sync_type": "manual",
  "force": false,
  "max_pages": 5,
  "start_page": 1
}
```

**请求参数**：
- `sync_type`: 同步类型
  - `full` - 完整同步（忽略时间戳）
  - `incremental` - 增量同步（基于时间戳）
  - `manual` - 手动同步
- `force`: 强制：是否强制同步（忽略限流）
- `max_pages`: 最大同步页数
- `start_page`: 起始页码

**响应**：
```json
{
  "sync_log_id": 1,
  "message": "同步开始",
  "status": "success"
}
```

### 3. 查看同步日志

```bash
GET /api/v1/pt-resources/sites/1/sync-logs?page=1&page_size=10
Authorization: Bearer {your_token}
```

### 4. 搜索资源

```bash
GET /api/v1/pt-resources?site_id=1&is_free=true&min_seeders=5&page=1&page_size=50
Authorization: Bearer {your_token}
```

**搜索过滤参数**：
- `site_id` - 站点 ID
- `category` - 分类（movie/tv/music/book/other）
- `is_free` - 免费种子
- `is_promotional` - 促销种子
- `min_seeders` - 最少做种数
- `resolution` - 分辨率（2160p/1080p/720p等）
- `source` - 来源（BluRay/WEB-DL等）
- `codec` - 编码（x264/x265/AV1等）
- `search` - 关键词搜索
- `page` - 页码
- `page_size` - 每页数量（1-500）

---

## 开发计划

### 短期目标
- [ ] 完成 MTeam API 接口适配器实现
- [ ] 实现 SyncLogService（同步日志服务）
- [ ] 添加基础错误处理和重试机制
- [ ] 完善资源去重和匹配逻辑

### 中期目标
- [ ] 集成 Celery 异步任务队列
- [ ] 实现定时自动同步
- [ ] 实现增量同步优化
- [ ] 添加更多认证方式支持

### 长期目标
- [ ] 支持更多 PT 站点类型（如 CHD、HDSky 等）
- [ ] 实现资源推荐系统
- [ ] 添加智能订阅功能
- [ ] 完善用户权限管理

---

## 数据模型

### pt_resources 表
主要字段：
- `id` - 主键
- `site_id` - 站点 ID（外键）
- `torrent_id` - 站点种子 ID
- `title` / `subtitle` - 标题/副标题
- `category` - 分类
- `size_bytes` - 文件大小
- `seeders` / `leechers` / `completions` - 做种/下载/完成数
- `is_free` / `is_discount` / `is_double_upload` - 免费状态
- `resolution` / `source` / `codec` - 媒体属性
- `imdb_id` / `douban_id` / `tmdb_id` - 外部 ID
- `download_url` - 下载链接
- `published_at` - 发布时间

### sync_logs 表
主要字段：
- `id` - 主键
- `site_id` - 站点 ID
- `sync_type` - 同步类型
- `status` - 状态（running/success/failed）
- `started_at` / `completed_at` / `duration` - 时间信息
- `resources_found` / `resources_new` / `resources_updated` - 统计信息
- `error_message` / `error_detail` - 错误信息

---

## 故障排除

### 调试日志
```bash
tail -f backend/data/logs/nasfusion.log
```

### 常见问题

**Q: 同步失败，提示 "Authentication failed"**
A: 检查 Passkey 是否正确或是否过期

**Q: 资源数据不完整**
A:
1. 检查 API 端点是否正确
2. 查看同步日志中的错误信息
3. 验证 MTeam 站点配置是否正确

**Q: 请求过于频繁**
A: 调整 `request_interval` 参数增加请求间隔

### 调试适配器

创建测试脚本 `test_mteam.py`：
```python
import asyncio
from app.adapters.pt_sites.mteam import MTeamAdapter

async def test():
    config = {
        "name": "MTeam",
        "base_url": "https://kp.m-team.cc",
        "auth_passkey": "your_passkey",
        "request_interval": 2,
    }

    adapter = MTeamAdapter(config)

    # 测试健康检查
    health = await adapter.health_check()
    print(f"Health check: {health}")

    # 测试获取资源
    resources = await adapter.fetch_resources(page=1, limit=10)
    print(f"Found {len(resources)} resources")
    for r in resources[:3]:
        print(f"  - {r.get('title')}")

asyncio.run(test())
```

---

## 部署说明

1. **配置 MTeam 参数**：参考"使用说明"章节进行配置
2. **测试同步功能**：使用 Postman 或 curl 测试 API 接口
3. **监控运行**：查看日志确保同步正常工作
4. **性能优化**：根据实际情况调整同步频率和并发数

此配置将确保系统能够稳定地从 MTeam 站点获取最新资源。