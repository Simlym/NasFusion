# PT站点元数据管理指南

## 概述

PT站点元数据包括分辨率、编码格式、来源、语言、国家等配置信息。NasFusion提供了完整的元数据管理功能。

### 为什么需要元数据管理？

1. **动态更新** - 站点配置可能变化，无需修改代码
2. **前端使用** - 提供下拉框选项，改善用户体验
3. **精准筛选** - 使用准确的ID进行资源筛选
4. **多站点支持** - 不同站点有不同的配置

---

## 元数据类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **video_codecs** | 视频编码格式 | H.264, H.265, VC-1 |
| **standards** | 分辨率/质量标准 | 1080p, 2160p, 8K |
| **sources** | 来源/制作方式 | BluRay, WEB-DL, HDTV |
| **languages** | 语言列表 | 中文, English, 日本語 |
| **countries** | 国家/地区 | 中国, 美国, 日本 |

---

## API接口

### 1. 同步站点元数据

**POST** `/api/v1/pt-sites/{site_id}/sync-metadata`

一次性获取站点的所有元数据配置。

```bash
POST http://localhost:8000/api/v1/pt-sites/1/sync-metadata
Authorization: Bearer {access_token}
```

**响应示例**：
```json
{
  "success": true,
  "message": "元数据同步完成",
  "stats": {
    "video_codecs": 5,
    "standards": 7,
    "sources": 10,
    "languages": 30,
    "countries": 150
  },
  "metadata": {
    "video_codecs": [
      {
        "id": "1",
        "name": "H.264(x264/AVC)",
        "order": "1"
      },
      {
        "id": "16",
        "name": "H.265(x265/HEVC)",
        "order": "2"
      }
    ],
    "standards": [
      {
        "id": "1",
        "name": "1080p",
        "order": "1"
      },
      {
        "id": "6",
        "name": "2160p",
        "order": "0"
      }
    ],
    "sources": [
      {
        "id": "8",
        "nameChs": "Web-DL",
        "nameCht": "Web-DL",
        "nameEng": "Web-DL",
        "order": "1"
      }
    ],
    "languages": [
      {
        "id": "28",
        "langName": "繁體中文",
        "flagpic": "tw.png",
        "siteLang": true,
        "subLang": true,
        "langTag": "zh_TW"
      }
    ],
    "countries": [
      {
        "id": "108",
        "name": "台灣, 中國",
        "pic": "tw.png"
      }
    ]
  }
}
```

---

### 2. 获取站点元数据

**GET** `/api/v1/pt-sites/{site_id}/metadata`

获取已缓存的元数据（无需重新请求站点API）。

```bash
GET http://localhost:8000/api/v1/pt-sites/1/metadata
Authorization: Bearer {access_token}
```

**响应示例（已同步）**：
```json
{
  "success": true,
  "metadata": {
    "video_codecs": [...],
    "standards": [...],
    "sources": [...],
    "languages": [...],
    "countries": [...]
  },
  "updated_at": "2025-11-07T12:00:00"
}
```

**响应示例（未同步）**：
```json
{
  "success": false,
  "message": "元数据未同步，请先调用 /sync-metadata",
  "metadata": null,
  "updated_at": null
}
```

---

## 使用场景

### 场景1：初始化站点配置

添加新站点后，立即同步元数据：

```bash
# 1. 添加站点
POST /api/v1/pt-sites
{
  "name": "MTeam",
  "type": "mteam",
  ...
}

# 2. 同步分类
POST /api/v1/pt-sites/1/sync-categories

# 3. 同步元数据
POST /api/v1/pt-sites/1/sync-metadata

# 4. 查看元数据
GET /api/v1/pt-sites/1/metadata
```

---

### 场景2：前端下拉框

在前端创建筛选表单时使用元数据：

```javascript
// 获取元数据
const response = await fetch('/api/v1/pt-sites/1/metadata', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { metadata } = await response.json();

// 渲染分辨率下拉框
<select name="resolution">
  <option value="">全部分辨率</option>
  {metadata.standards.map(std => (
    <option value={std.id}>{std.name}</option>
  ))}
</select>

// 渲染编码下拉框
<select name="codec">
  <option value="">全部编码</option>
  {metadata.video_codecs.map(codec => (
    <option value={codec.id}>{codec.name}</option>
  ))}
</select>

// 渲染来源下拉框
<select name="source">
  <option value="">全部来源</option>
  {metadata.sources.map(source => (
    <option value={source.id}>{source.nameChs}</option>
  ))}
</select>
```

---

### 场景3：资源搜索时使用

在搜索资源时，使用元数据ID进行精准筛选：

```bash
# 搜索 4K + H.265 + WEB-DL 资源
POST /api/v1/pt-resources/sites/1/sync
{
  "sync_type": "manual",
  "max_pages": 5,
  "filters": {
    "standard": "6",      # 2160p (来自metadata.standards)
    "videoCodec": "16",   # H.265 (来自metadata.video_codecs)
    "source": "8"         # WEB-DL (来自metadata.sources)
  }
}
```

---

### 场景4：多语言/多地区筛选

使用语言和国家元数据进行内容筛选：

```javascript
// 仅显示中文内容
const chineseLanguages = metadata.languages.filter(
  lang => lang.langName.includes('中文')
);

// 仅显示中国/台湾地区内容
const chineseCountries = metadata.countries.filter(
  country => country.name.includes('中國') || country.name.includes('台灣')
);
```

---

## MTeam元数据示例

### 视频编码 (video_codecs)

```json
[
  { "id": "1", "name": "H.264(x264/AVC)", "order": "1" },
  { "id": "16", "name": "H.265(x265/HEVC)", "order": "2" },
  { "id": "2", "name": "VC-1", "order": "3" },
  { "id": "4", "name": "MPEG-2", "order": "7" },
  { "id": "22", "name": "AVS", "order": "11" }
]
```

### 分辨率/标准 (standards)

```json
[
  { "id": "1", "name": "1080p", "order": "1" },
  { "id": "2", "name": "1080i", "order": "2" },
  { "id": "3", "name": "720p", "order": "3" },
  { "id": "6", "name": "2160p", "order": "0" },
  { "id": "7", "name": "8K", "order": "6" }
]
```

### 来源 (sources)

```json
[
  { "id": "1", "nameChs": "BluRay", "order": "0" },
  { "id": "8", "nameChs": "Web-DL", "order": "1" },
  { "id": "3", "nameChs": "HDTV", "order": "3" },
  { "id": "5", "nameChs": "Remux", "order": "5" },
  { "id": "2", "nameChs": "DVD", "order": "2" },
  { "id": "10", "nameChs": "CD", "order": "7" }
]
```

---

## 数据库设计

元数据存储在 `pt_sites` 表的 `metadata_cache` 字段（JSON类型）：

| 字段 | 类型 | 说明 |
|------|------|------|
| metadata_cache | JSON | 元数据缓存 |
| metadata_updated_at | DateTime | 最后更新时间 |

**优点**：
- 无需额外表结构
- 查询速度快
- 易于扩展

---

## 最佳实践

### 1. 定期更新

站点元数据可能更新，建议定期同步（每月一次）：

```bash
# 手动触发
POST /api/v1/pt-sites/1/sync-metadata

# 或在站点设置页面添加"刷新元数据"按钮
```

### 2. 首次配置时同步

添加新站点的推荐流程：

```
1. 添加站点基础信息
2. 同步分类 (sync-categories)
3. 同步元数据 (sync-metadata)
4. 测试资源同步
```

### 3. 缓存前端

前端可以缓存元数据，减少请求：

```javascript
// LocalStorage缓存
const cacheKey = `site_${siteId}_metadata`;
const cached = localStorage.getItem(cacheKey);

if (cached) {
  const { metadata, timestamp } = JSON.parse(cached);

  // 7天内有效
  if (Date.now() - timestamp < 7 * 24 * 60 * 60 * 1000) {
    return metadata;
  }
}

// 重新获取
const metadata = await fetchMetadata(siteId);
localStorage.setItem(cacheKey, JSON.stringify({
  metadata,
  timestamp: Date.now()
}));
```

### 4. 错误处理

元数据同步失败不应影响核心功能：

```javascript
try {
  await syncMetadata(siteId);
} catch (error) {
  console.warn('元数据同步失败，使用默认值', error);
  // 使用硬编码的默认值
}
```

---

## 适配器开发指南

如果要为新的PT站点实现元数据支持，需要：

### 1. 添加API端点

```python
# 在适配器的 __init__ 中
self.api_endpoints = {
    "video_codec_list": "/api/torrent/videoCodecList",
    "standard_list": "/api/torrent/standardList",
    "source_list": "/api/torrent/sourceList",
    "langs": "/api/system/langs",
    "country_list": "/api/system/countryList",
}
```

### 2. 实现 fetch_metadata 方法

```python
async def fetch_metadata(self) -> Dict[str, Any]:
    """获取站点所有元数据"""
    metadata = {}

    # 获取各类元数据
    metadata["video_codecs"] = await self._fetch_video_codecs()
    metadata["standards"] = await self._fetch_standards()
    metadata["sources"] = await self._fetch_sources()
    # ...

    return metadata
```

### 3. 处理不同响应格式

不同站点的API响应格式可能不同，需要适配：

```python
# MTeam格式
data = response.get("data", [])

# 其他站点可能是
data = response.get("items", [])
# 或
data = response.get("result", {}).get("list", [])
```

---

## 故障排查

### 问题1：同步失败

**症状**：POST `/sync-metadata` 返回500错误

**排查步骤**：
1. 检查站点API是否可访问
2. 检查API Key是否有效
3. 查看日志：`tail -f backend/data/logs/nasfusion.log | grep metadata`

### 问题2：元数据为空

**症状**：GET `/metadata` 返回 `metadata: null`

**解决方案**：
```bash
# 先同步
POST /api/v1/pt-sites/1/sync-metadata

# 再查询
GET /api/v1/pt-sites/1/metadata
```

### 问题3：部分元数据缺失

**症状**：某些字段为空数组

**原因**：站点API可能不返回某些类型的元数据

**解决方案**：
- 使用适配器中的默认映射表
- 或在前端显示"暂无数据"

---

## API总结

| 接口 | 方法 | 说明 |
|------|------|------|
| `/pt-sites/{site_id}/sync-metadata` | POST | 同步元数据 |
| `/pt-sites/{site_id}/metadata` | GET | 获取元数据缓存 |
| `/pt-sites/{site_id}/sync-categories` | POST | 同步分类 |
| `/pt-sites/{site_id}/categories` | GET | 获取分类列表 |

---

## 完整使用流程

```bash
# 1. 添加站点
POST /api/v1/pt-sites
{
  "name": "MTeam",
  "type": "mteam",
  "domain": "kp.m-team.cc",
  "auth_type": "passkey",
  "auth_passkey": "your_api_key"
}
# → 得到 site_id = 1

# 2. 同步分类
POST /api/v1/pt-sites/1/sync-categories
# → 45个分类已同步

# 3. 同步元数据
POST /api/v1/pt-sites/1/sync-metadata
# → 视频编码、分辨率、来源等已缓存

# 4. 查看分类（树形）
GET /api/v1/pt-sites/1/categories?tree=true
# → 用于前端分类选择器

# 5. 查看元数据
GET /api/v1/pt-sites/1/metadata
# → 用于前端下拉框

# 6. 开始同步资源
POST /api/v1/pt-resources/sites/1/sync
{
  "sync_type": "manual",
  "max_pages": 10
}
```

---

## 总结

元数据管理系统的优势：

✅ **动态配置** - 无需修改代码，API驱动
✅ **前端友好** - 直接用于下拉框和筛选器
✅ **精准筛选** - 使用准确的ID而非模糊匹配
✅ **性能优化** - 缓存机制，减少API请求
✅ **多站点支持** - 每个站点独立的元数据

建议在站点首次配置时同步元数据，并在前端实现缓存策略以提升用户体验。
