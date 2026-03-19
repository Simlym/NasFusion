# PT站点元数据管理重构文档

## 📋 概述

本次重构将PT站点元数据管理从**JSON缓存**方式改为**独立数据表**方式，实现了统一的架构设计和动态映射机制。

### 重构时间
2025年1月

### 重构范围
- 数据库模型层
- 服务层
- API层
- 适配器层

---

## 🎯 重构目标

### 问题

**重构前的架构问题**：

1. **设计不一致**
   - `pt_categories` 使用独立表
   - 其他元数据（video_codecs、standards、sources等）使用JSON存储在 `pt_sites.metadata_cache`

2. **硬编码映射**
   - 适配器中硬编码了ID到值的映射字典（如 `mteam.py:83-146`）
   - 站点修改ID映射时需要修改代码

3. **僵尸数据**
   - `metadata_cache` 通过API同步但从未被实际使用
   - 适配器使用的是硬编码映射，而非数据库映射

### 解决方案

**重构后的架构**：

1. ✅ **统一建表** - 所有元数据都使用独立表存储
2. ✅ **动态映射** - 适配器从数据库加载映射，支持fallback到硬编码
3. ✅ **自动同步** - 创建站点时自动同步所有元数据

---

## 📊 数据库变更

### 新增的表

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `pt_categories` | 分类表（已存在，移入pt_metadata.py） | category_id, mapped_category |
| `pt_video_codecs` | 视频编码表 | codec_id, mapped_value (H.264/H.265等) |
| `pt_audio_codecs` | 音频编码表 | codec_id, mapped_value (AAC/DTS等) |
| `pt_standards` | 分辨率/标准表 | standard_id, mapped_value (1080p/2160p等) |
| `pt_sources` | 来源表 | source_id, mapped_value (BluRay/WEB-DL等) |
| `pt_languages` | 语言表 | language_id, mapped_value |
| `pt_countries` | 国家/地区表 | country_id, mapped_value |

### 表结构统一设计

所有元数据表都遵循相同的结构：

```python
class PTMetadataBase:
    id: int                      # 主键
    site_id: int                 # 站点ID（外键）
    {type}_id: str               # 站点原始ID（如 "419", "6"等）

    # 多语言名称
    name: str                    # 名称
    name_chs: str                # 简体中文名称
    name_cht: str                # 繁体中文名称
    name_eng: str                # 英文名称

    # 映射和排序
    mapped_value: str            # 标准化映射值（核心字段！）
    description: str             # 描述
    order: int                   # 排序顺序

    # 状态
    is_active: bool              # 是否启用

    # 原始数据
    raw_data: JSON               # API返回的原始JSON

    # 时间戳
    created_at: datetime
    updated_at: datetime
```

### 删除的字段

从 `pt_sites` 表中删除：
- ❌ `metadata_cache` (JSON)
- ❌ `metadata_updated_at` (DateTime)

---

## 🔄 数据流变化

### 重构前

```
┌─────────────┐
│ MTeam API   │
│ {           │
│   "id": "6" │  ──┐
│ }           │    │
└─────────────┘    │
                   │
         ┌─────────▼────────────┐
         │ MTeamAdapter         │
         │ 硬编码映射:          │
         │ {"6": "2160p"}       │
         └─────────┬────────────┘
                   │
         ┌─────────▼────────────┐
         │ pt_resources表       │
         │ resolution: "2160p"  │
         └──────────────────────┘

         ┌──────────────────────┐
         │ pt_sites表           │
         │ metadata_cache: {...}│  ← 僵尸数据
         └──────────────────────┘
```

### 重构后

```
┌─────────────┐
│ MTeam API   │
│ fetch_      │
│ metadata()  │
└──────┬──────┘
       │
       ▼
┌────────────────────────────┐
│ PTMetadataService          │
│ sync_all_metadata()        │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│ pt_standards 表            │
│ standard_id: "6"           │
│ mapped_value: "2160p"      │
└────────┬───────────────────┘
         │
         │ 加载映射
         ▼
┌────────────────────────────┐
│ PTResourceService          │
│ _get_site_adapter(db)      │
└────────┬───────────────────┘
         │
         │ 传递metadata_mappings
         ▼
┌────────────────────────────┐
│ MTeamAdapter               │
│ _get_mapped_value()        │
│ 1. 优先: metadata_mappings │
│ 2. Fallback: 硬编码字典    │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│ pt_resources表             │
│ resolution: "2160p"        │
└────────────────────────────┘
```

---

## 🚀 新增功能

### 1. PTMetadataService

**文件**: `app/services/pt_metadata_service.py`

**核心方法**：

```python
# 同步所有元数据
await PTMetadataService.sync_all_metadata(db, site, metadata)

# 获取映射字典（供适配器使用）
mappings = await PTMetadataService.get_metadata_mappings(db, site_id)
# 返回: MetadataMappings(
#   video_codecs={"16": "H.265"},
#   standards={"6": "2160p"},
#   ...
# )

# 独立同步方法
await PTMetadataService.sync_video_codecs(db, site, codecs_data)
await PTMetadataService.sync_standards(db, site, standards_data)
# ... 其他类型
```

**智能映射规则**：

自动识别常见值并映射到标准化值：

```python
VIDEO_CODEC_MAPPING_RULES = {
    "H.264": ["h264", "avc", "x264", "h.264"],
    "H.265": ["h265", "hevc", "x265", "h.265"],
    ...
}
```

### 2. 适配器改造

**文件**: `app/adapters/pt_sites/mteam.py`

**改造内容**：

```python
# 1. 构造函数支持metadata_mappings
def __init__(self, config, metadata_mappings=None):
    self.metadata_mappings = metadata_mappings or {}

# 2. 新增辅助方法
def _get_mapped_value(self, metadata_type, original_id, fallback_map):
    # 优先使用动态映射
    if metadata_type in self.metadata_mappings:
        value = self.metadata_mappings[metadata_type].get(original_id)
        if value:
            return value
    # Fallback到硬编码
    return fallback_map.get(original_id)

# 3. 使用动态映射
resolution = self._get_mapped_value("standards", standard_id, self.resolution_map)
```

**向后兼容**：
- 保留硬编码映射作为fallback
- 如果元数据未同步，自动使用硬编码
- 新站点会自动同步元数据

### 3. API接口

**新增/修改的接口**：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/pt-sites/{site_id}/sync-all-metadata` | POST | 同步所有元数据 |
| `/pt-sites/{site_id}/metadata` | GET | 获取所有元数据 |
| `/pt-sites/{site_id}/video-codecs` | GET | 获取视频编码列表 |
| `/pt-sites/{site_id}/audio-codecs` | GET | 获取音频编码列表 |
| `/pt-sites/{site_id}/standards` | GET | 获取分辨率列表 |
| `/pt-sites/{site_id}/sources` | GET | 获取来源列表 |
| `/pt-sites/{site_id}/languages` | GET | 获取语言列表 |
| `/pt-sites/{site_id}/countries` | GET | 获取国家/地区列表 |

**请求示例**：

```bash
# 同步元数据
POST /api/v1/pt-sites/1/sync-all-metadata

# 响应
{
  "success": true,
  "message": "元数据同步完成",
  "stats": {
    "video_codecs": 5,
    "audio_codecs": 10,
    "standards": 7,
    "sources": 8,
    "languages": 30,
    "countries": 25
  },
  "synced_types": ["video_codecs", "standards", ...]
}

# 获取视频编码
GET /api/v1/pt-sites/1/video-codecs

# 响应
{
  "site_id": 1,
  "site_name": "MTeam",
  "total": 5,
  "video_codecs": [
    {
      "id": 1,
      "codec_id": "16",
      "name": "H.265",
      "mapped_value": "H.265",
      ...
    }
  ]
}
```

### 4. 自动同步机制

**触发时机**：创建站点时自动同步

**实现位置**: `PTSiteService.create_site()`

```python
async def create_site(db, site_data):
    # 1. 创建站点
    site = PTSite(...)
    await db.commit()

    # 2. 自动同步元数据（新增！）
    await PTSiteService._auto_sync_metadata(db, site)

    return site
```

**同步内容**：
1. 同步分类（Categories）
2. 同步其他元数据（video_codecs, standards等）

**错误处理**：
- 元数据同步失败不影响站点创建
- 记录warning日志，用户可手动重新同步

---

## 📝 数据迁移

### 迁移脚本

**文件**: `backend/scripts/migrate_metadata.py`

**使用方法**：

```bash
# 1. 对所有站点重新同步元数据
python scripts/migrate_metadata.py

# 2. 仅检查是否有旧字段
python scripts/migrate_metadata.py --check-only

# 3. 删除旧字段（谨慎！）
python scripts/migrate_metadata.py --drop-old-fields
```

**脚本功能**：
- ✅ 自动检测所有活跃站点
- ✅ 逐个站点调用元数据同步
- ✅ 显示详细的进度和结果
- ✅ 错误处理和日志记录

**示例输出**：

```
============================================================
🔧 PT站点元数据迁移脚本
============================================================

📊 找到 2 个活跃站点，开始迁移...
============================================================

[1/2] 正在处理站点: MTeam
  - 类型: mteam
  - 域名: kp.m-team.cc
  ✅ 元数据同步成功
------------------------------------------------------------

[2/2] 正在处理站点: CHD
  - 类型: chd
  - 域名: chd.im
  ✅ 元数据同步成功
------------------------------------------------------------

✅ 迁移完成！
  - 成功: 2 个站点
  - 失败: 0 个站点
```

---

## 🔍 使用示例

### 前端使用场景

**场景1：获取下拉框选项**

```typescript
// 获取视频编码选项
const response = await api.get(`/pt-sites/${siteId}/video-codecs`)
const options = response.video_codecs.map(codec => ({
  value: codec.codec_id,
  label: codec.mapped_value,  // "H.265"
  description: codec.name      // "H.265/HEVC"
}))

// 用于筛选资源
<Select options={options} v-model="filter.videoCodec" />
```

**场景2：资源搜索过滤**

```typescript
// 用户选择：2160p + H.265 + BluRay
const searchParams = {
  site_id: 1,
  standard: "6",      // 2160p的ID
  videoCodec: "16",   // H.265的ID
  source: "1"         // BluRay的ID
}

// 后端会自动转换这些ID为文本值存储
```

### 后端使用场景

**场景1：创建新站点（自动同步）**

```python
# 创建站点时自动同步元数据
site = await PTSiteService.create_site(db, site_data)
# ↑ 内部会自动调用 _auto_sync_metadata()
```

**场景2：手动重新同步**

```python
# 调用API接口
POST /api/v1/pt-sites/1/sync-all-metadata
```

**场景3：适配器获取映射**

```python
# PTResourceService 自动加载映射
adapter = await PTResourceService._get_site_adapter(site, db)
# ↑ 内部会调用 PTMetadataService.get_metadata_mappings()
```

---

## ⚠️ 注意事项

### 1. 向后兼容性

- ✅ 保留了硬编码映射作为fallback
- ✅ 旧站点未同步元数据时仍能正常工作
- ✅ 迁移脚本不会破坏现有数据

### 2. 数据库迁移

**SQLite用户**：
- 删除旧字段需要手动处理或等待完整迁移
- 建议运行迁移脚本后重建数据库

**PostgreSQL用户**：
- 可以直接使用 `ALTER TABLE DROP COLUMN`
- 迁移脚本会自动处理

### 3. 性能影响

**优化点**：
- ✅ 元数据映射在适配器初始化时一次性加载
- ✅ 使用索引优化查询（site_id, order）
- ✅ 前端可缓存元数据列表

**潜在问题**：
- 首次创建站点时会同步元数据（需要网络请求）
- 可能需要几秒钟时间

### 4. 错误处理

**元数据同步失败**：
- 不影响站点创建
- 记录warning日志
- 用户可手动重新同步

**适配器不支持**：
- 某些站点可能不支持元数据API
- 自动fallback到硬编码映射
- 不影响核心功能

---

## 📚 相关文档

- [数据库设计文档](database_design.md)
- [分类管理指南](category_management.md)
- [MTeam集成指南](mteam_integration_guide.md)

---

## 🎉 重构收益

### 技术层面

1. **统一架构** - 所有元数据使用相同的表结构和处理逻辑
2. **动态映射** - 站点修改映射规则时无需修改代码
3. **可维护性** - 代码更清晰，逻辑更统一
4. **扩展性** - 支持未来新增更多元数据类型

### 业务层面

1. **降低维护成本** - 减少硬编码，提高灵活性
2. **提升用户体验** - 前端可以直接获取最新的元数据选项
3. **数据一致性** - 统一的数据源，避免不一致

### 数据质量

1. **自动更新** - 站点修改元数据时可及时同步
2. **智能映射** - 自动识别常见值并标准化
3. **人工干预** - 支持手动调整映射（未来功能）

---

## 🔮 未来计划

### 短期（已完成）

- ✅ 统一元数据表结构
- ✅ 实现动态映射机制
- ✅ 提供完整的API接口
- ✅ 编写迁移脚本

### 中期（待实现）

- ⏳ 前端UI适配新接口
- ⏳ 支持手动调整元数据映射
- ⏳ 元数据变更通知机制
- ⏳ 多站点元数据聚合

### 长期（规划中）

- 💡 机器学习自动映射优化
- 💡 元数据版本管理
- 💡 跨站点元数据标准化

---

## 📞 问题反馈

如遇到问题，请检查：

1. **数据库是否正确迁移**
   ```bash
   python scripts/migrate_metadata.py --check-only
   ```

2. **元数据是否已同步**
   ```bash
   GET /api/v1/pt-sites/{site_id}/metadata
   ```

3. **日志中是否有错误**
   ```bash
   tail -f logs/app.log | grep metadata
   ```

如问题仍未解决，请提交Issue并附上：
- 站点类型和版本
- 错误日志
- 复现步骤
