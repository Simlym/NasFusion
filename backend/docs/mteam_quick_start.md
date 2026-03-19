# MTeam 快速开始指南

## 更新内容

MTeam适配器已更新为使用真实的API接口！

### 已实现的功能
- ✅ 使用 `x-api-key` 认证（存储在 `auth_passkey` 字段）
- ✅ POST `/api/torrent/search` 搜索资源
- ✅ 完整的字段映射（分类、分辨率、来源、编码等）
- ✅ IMDB和豆瓣ID自动提取
- ✅ 促销类型识别（FREE、折扣、双倍上传）
- ✅ 请求头完全匹配MTeam要求

---

## 快速开始

### 步骤1：添加MTeam站点

```bash
POST http://localhost:8000/api/v1/pt-sites
Content-Type: application/json
Authorization: Bearer {your_access_token}

{
  "name": "MTeam",
  "type": "mteam",
  "domain": "kp.m-team.cc",
  "base_url": "https://kp.m-team.cc",
  "auth_type": "passkey",
  "auth_passkey": "你的x-api-key",
  "sync_enabled": true,
  "sync_strategy": "page_based",
  "sync_interval": 60,
  "request_interval": 2,
  "max_requests_per_day": 5000
}
```

**重要说明**：
- `auth_passkey` 字段实际存储的是 `x-api-key`
- 从MTeam网站的个人设置中获取你的 API Key

### 步骤2：触发资源同步

```bash
POST http://localhost:8000/api/v1/pt-resources/sites/1/sync
Content-Type: application/json
Authorization: Bearer {your_access_token}

{
  "sync_type": "manual",
  "force": false,
  "max_pages": 5,
  "start_page": 1
}
```

**同步参数说明**：
- `max_pages`: 5 - 将同步前5页（每页100条，共500条资源）
- `start_page`: 1 - 从第一页开始
- `sync_type`: "manual" - 手动同步
- `force`: false - 遵守请求间隔限制

**响应示例**：
```json
{
  "sync_log_id": 1,
  "message": "同步任务已完成",
  "status": "success"
}
```

### 步骤3：查看同步结果

```bash
# 查看资源列表
GET http://localhost:8000/api/v1/pt-resources?site_id=1&page=1&page_size=20
Authorization: Bearer {your_access_token}
```

**响应示例**：
```json
{
  "total": 500,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "site_id": 1,
      "torrent_id": "1066381",
      "title": "Operation Hadal 2025 2160p iQIYI WEB-DL AAC2.0 H.265-MWeb",
      "subtitle": "蛟龙行动 | 2025 | 中国大陆 | 剧情 动作 战争",
      "category": "movie",
      "size_bytes": 3196074283,
      "size_gb": 2.98,
      "size_human_readable": "2.98 GB",
      "seeders": 653,
      "leechers": 12,
      "completions": 832,
      "is_free": true,
      "is_discount": false,
      "is_double_upload": false,
      "is_promotional": true,
      "promotion_type": "free",
      "promotion_expire_at": "2025-11-07T23:48:14",
      "resolution": "2160p",
      "source": "WEB-DL",
      "codec": "H.265",
      "audio": ["AAC"],
      "quality_tags": ["4k"],
      "imdb_id": "tt32515812",
      "douban_id": "35295960",
      "published_at": "2025-11-07T11:48:14",
      "created_at": "2025-11-07T12:00:00"
    }
  ]
}
```

---

## API端点总览

### 1. 资源列表（带过滤）

```bash
GET /api/v1/pt-resources?site_id=1&is_free=true&resolution=2160p&min_seeders=10&page=1&page_size=50
```

**支持的过滤参数**：
- `site_id` - 站点ID
- `category` - 分类（movie/tv/music/book/other）
- `is_free` - 仅免费资源
- `is_promotional` - 仅促销资源
- `min_seeders` - 最小做种数
- `resolution` - 分辨率（2160p/1080p/720p等）
- `source` - 来源（BluRay/WEB-DL/HDTV等）
- `codec` - 编码（H.264/H.265等）
- `search` - 搜索关键词（标题）
- `page` - 页码（默认1）
- `page_size` - 每页大小（1-500，默认50）

### 2. 资源详情

```bash
GET /api/v1/pt-resources/{resource_id}
```

### 3. 删除资源

```bash
DELETE /api/v1/pt-resources/{resource_id}
```

### 4. 查看同步日志

```bash
GET /api/v1/pt-resources/sites/1/sync-logs?page=1&page_size=10
```

---

## 字段映射说明

### 分类映射
- `401`, `419` → `movie` (电影)
- `403` → `tv` (电视剧)
- `402` → `tv` (纪录片)
- `404` → `tv` (综艺)
- `405` → `tv` (动漫)
- `406`, `407` → `music` (音乐/MV)
- `408`, `409` → `other` (体育/其他)

### 分辨率映射
- `1` → `1080p`
- `2` → `1080i`
- `3` → `720p`
- `6` → `2160p` (4K)
- `7` → `8K`

### 来源映射
- `1` → `BluRay` (蓝光)
- `2` → `DVD`
- `3` → `HDTV`
- `4`, `8` → `WEB-DL`
- `5` → `Remux`
- `6` → `Encode` (压制)

### 编码映射
- `1` → `H.264/AVC`
- `6`, `16` → `H.265/HEVC`
- `2` → `VC-1`
- `3` → `MPEG-2`

### 促销类型
- `FREE` → 免费下载
- `_2X` → 2倍上传
- `_2X_FREE` → 免费 + 2倍上传
- `PERCENT_50` → 50%下载
- `_2X_50_PERCENT` → 50%下载 + 2倍上传

---

## 常见使用场景

### 场景1：获取所有免费4K电影

```bash
GET /api/v1/pt-resources?is_free=true&resolution=2160p&category=movie&min_seeders=5&page=1&page_size=100
```

### 场景2：搜索特定电影

```bash
GET /api/v1/pt-resources?search=蛟龙行动&page=1&page_size=20
```

### 场景3：查看高质量蓝光资源

```bash
GET /api/v1/pt-resources?source=BluRay&resolution=1080p&min_seeders=10&page=1&page_size=50
```

### 场景4：获取最新电视剧

```bash
GET /api/v1/pt-resources?category=tv&page=1&page_size=50
```

---

## 测试建议

### 1. 小规模测试
首次使用时，建议先同步少量数据进行测试：
```json
{
  "sync_type": "manual",
  "max_pages": 1,
  "start_page": 1
}
```

### 2. 检查日志
查看后端日志以确认同步过程：
```bash
tail -f backend/data/logs/nasfusion.log | grep -i mteam
```

### 3. 验证数据
同步后检查数据库中的资源数量：
```sql
SELECT COUNT(*) FROM pt_resources WHERE site_id = 1;
SELECT * FROM pt_resources WHERE site_id = 1 LIMIT 10;
```

---

## 性能建议

### 1. 请求间隔
- 建议设置 `request_interval = 2` 秒
- MTeam限流较严格，过快请求可能被封禁

### 2. 批量同步
- 每页100条是最优配置
- 同步大量数据时分批进行（每次5-10页）

### 3. 定时任务（待实现）
```python
# 未来将支持定时同步
# 每小时同步一次新资源
{
  "sync_enabled": true,
  "sync_interval": 60,  # 分钟
  "sync_strategy": "time_based"
}
```

---

## 故障排查

### 问题1：认证失败
**症状**：同步时提示 "MTeam API error: ..."

**解决方案**：
1. 检查 `auth_passkey` 是否填写正确的 x-api-key
2. 确认API Key未过期
3. 检查MTeam账户是否正常

### 问题2：无法获取资源
**症状**：同步成功但资源数量为0

**解决方案**：
1. 检查MTeam API是否有数据
2. 查看日志中的错误信息
3. 尝试访问 https://api.m-team.cc 确认API可访问

### 问题3：请求被限流
**症状**：出现 HTTP 429 Too Many Requests

**解决方案**：
1. 增加 `request_interval` 到 3-5 秒
2. 减少 `max_pages` 参数
3. 等待一段时间后再尝试

---

## 下一步

- [ ] 实现Celery异步任务（后台同步）
- [ ] 添加增量同步策略
- [ ] 实现定时任务调度
- [ ] 支持RSS订阅
- [ ] 添加资源去重功能

---

## 技术细节

### API请求示例

**请求头**：
```http
POST /api/torrent/search HTTP/1.1
Host: api.m-team.cc
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/json
Accept: application/json, text/plain, */*
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
x-api-key: your_api_key_here
```

**请求体**：
```json
{
  "mode": "normal",
  "visible": 1,
  "categories": [],
  "pageNumber": 1,
  "pageSize": 100
}
```

**响应格式**：
```json
{
  "code": "0",
  "message": "SUCCESS",
  "data": {
    "pageNumber": "1",
    "pageSize": "100",
    "total": "10000",
    "totalPages": "100",
    "data": [...]
  }
}
```

---

如有问题，请查看完整日志或提Issue！
