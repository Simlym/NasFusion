# PT站点分类管理指南

## 概述

每个PT站点都有自己的分类体系，NasFusion提供了完整的分类管理功能：

### 核心功能
- ✅ **动态分类同步** - 从PT站点API获取最新分类信息
- ✅ **自动映射** - 智能映射到标准分类（movie/tv/music等）
- ✅ **树形结构** - 支持父子分类关系
- ✅ **多语言支持** - 中文简体/繁体/英文
- ✅ **手动调整** - 可手动修改自动映射结果

---

## 标准分类体系

系统将各站点的分类统一映射到以下标准分类：

| 标准分类 | 说明 | 示例 |
|---------|------|------|
| `movie` | 电影 | 电影/SD, 电影/HD, 电影/BD |
| `tv` | 电视剧集 | 电视剧, 综艺, 纪录片 |
| `music` | 音乐 | 音乐, MV, 演唱会 |
| `book` | 书籍 | 电子书, 有声书 |
| `anime` | 动漫 | 动画, 番剧 |
| `adult` | 成人内容 | AV, IV, H-ACG |
| `game` | 游戏 | PC游戏, TV游戏 |
| `other` | 其他 | 软件, 运动, 教育 |

---

## API接口

### 1. 同步站点分类

**POST** `/api/v1/pt-sites/{site_id}/sync-categories`

```bash
POST http://localhost:8000/api/v1/pt-sites/1/sync-categories
Authorization: Bearer {access_token}
```

**功能**：
1. 调用站点API获取最新分类列表
2. 自动映射到标准分类
3. 识别成人内容分类
4. 更新数据库

**响应示例**：
```json
{
  "success": true,
  "message": "分类同步完成",
  "stats": {
    "total": 45,
    "created": 45,
    "updated": 0,
    "skipped": 0
  }
}
```

---

### 2. 获取站点分类列表

**GET** `/api/v1/pt-sites/{site_id}/categories`

**参数**：
- `tree` (boolean) - 是否返回树形结构，默认false
- `include_inactive` (boolean) - 是否包含未启用的分类，默认false

**扁平列表示例**：
```bash
GET http://localhost:8000/api/v1/pt-sites/1/categories
```

```json
{
  "site_id": 1,
  "site_name": "MTeam",
  "total": 45,
  "categories": [
    {
      "id": 1,
      "site_id": 1,
      "category_id": "401",
      "name_chs": "电影/SD",
      "name_cht": "電影/SD",
      "name_eng": "Movie/SD",
      "parent_id": "100",
      "order": 1,
      "image": "moviesd.png",
      "mapped_category": "movie",
      "is_adult": false,
      "is_active": true
    }
  ]
}
```

**树形结构示例**：
```bash
GET http://localhost:8000/api/v1/pt-sites/1/categories?tree=true
```

```json
{
  "site_id": 1,
  "site_name": "MTeam",
  "total": 10,
  "categories": [
    {
      "category_id": "100",
      "name_chs": "电影",
      "mapped_category": "movie",
      "children": [
        {
          "category_id": "401",
          "name_chs": "电影/SD",
          "parent_id": "100",
          "children": []
        },
        {
          "category_id": "419",
          "name_chs": "电影/HD",
          "parent_id": "100",
          "children": []
        }
      ]
    }
  ]
}
```

---

### 3. 更新分类映射

**PUT** `/api/v1/pt-sites/{site_id}/categories/{category_id}`

用于手动修正自动映射不准确的情况。

```bash
PUT http://localhost:8000/api/v1/pt-sites/1/categories/404?mapped_category=tv
Authorization: Bearer {access_token}
```

**参数**：
- `mapped_category` (required) - 标准分类，可选值：
  - `movie` / `tv` / `music` / `book` / `anime` / `adult` / `game` / `other`

**响应**：
```json
{
  "success": true,
  "message": "分类映射已更新",
  "category": {
    "id": 4,
    "category_id": "404",
    "name_chs": "纪录",
    "mapped_category": "tv"
  }
}
```

---

## 自动映射规则

系统根据分类名称（中英文）自动映射到标准分类，映射规则：

| 标准分类 | 关键词 |
|---------|--------|
| movie | 电影, movie, 電影, film |
| tv | 电视, 剧集, 综艺, tv, series, 電視, 劇集, 綜藝 |
| music | music, 音乐, 音樂, mv, 演唱 |
| book | 电子书, 有声书, 電子書, 有聲書, ebook, audiobook |
| anime | 动画, 动漫, 動畫, 動漫, anime |
| game | 游戏, 遊戲, game |
| adult | av, adult, 成人, iv, h- |
| documentary | 纪录, 紀錄, documentary, bbc |
| sport | 运动, 體育, 運動, sports |
| software | 软件, 軟體, software |

**特殊规则**：
- 成人内容具有最高优先级
- 名称中包含关键词即可匹配
- 不区分大小写
- 无法匹配则归为 `other`

---

## 使用场景

### 场景1：首次配置站点

添加新站点后，立即同步分类：

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

# 3. 查看分类
GET /api/v1/pt-sites/1/categories?tree=true
```

### 场景2：按分类搜索资源

```bash
# 1. 获取电影分类ID
GET /api/v1/pt-sites/1/categories

# 筛选 mapped_category = "movie" 的分类
# 得到: 401, 419, 420, 421, 439

# 2. 使用分类ID搜索
POST /api/v1/pt-resources/sites/1/sync
{
  "sync_type": "manual",
  "max_pages": 1,
  "categories": ["401", "419"]  # 仅同步电影分类
}
```

### 场景3：过滤成人内容

```bash
# 获取非成人内容的分类
GET /api/v1/pt-sites/1/categories

# 在前端过滤 is_adult = false 的分类
# 或在同步时排除成人分类
```

### 场景4：修正错误映射

```bash
# 发现"纪录"被映射到"other"，应该是"tv"
PUT /api/v1/pt-sites/1/categories/404?mapped_category=tv
```

---

## MTeam分类示例

MTeam站点的分类结构（已映射）：

```
电影 (100) → movie
  ├─ 电影/SD (401) → movie
  ├─ 电影/HD (419) → movie
  ├─ 电影/DVDiSo (420) → movie
  ├─ 电影/Blu-Ray (421) → movie
  └─ 电影/Remux (439) → movie

影剧/综艺 (105) → tv
  ├─ 影剧/综艺/SD (403) → tv
  ├─ 影剧/综艺/HD (402) → tv
  ├─ 影剧/综艺/BD (438) → tv
  └─ 影剧/综艺/DVDiSo (435) → tv

Music (110) → music
  ├─ Music(无损) (434) → music
  └─ 演唱 (406) → music

纪录 (444) → tv
  └─ 纪录 (404) → tv

动漫 (449) → anime
  └─ 动画 (405) → anime

遊戲 (447) → game
  ├─ PC游戏 (423) → game
  └─ TV遊戲 (448) → game

其他 (450) → other
  ├─ 電子書 (427) → book
  ├─ 有聲書 (442) → book
  ├─ 软件 (422) → other
  ├─ 运动 (407) → other
  ├─ Misc(其他) (409) → other
  └─ 教育影片 (451) → other

AV(有码) (115) → adult
  ├─ AV(有码)/HD Censored (410) → adult
  ├─ AV(有码)/SD Censored (424) → adult
  ├─ AV(有码)/DVDiSo Censored (437) → adult
  └─ AV(有码)/Blu-Ray Censored (431) → adult

AV(无码) (120) → adult
  ├─ AV(无码)/HD Uncensored (429) → adult
  ├─ AV(无码)/SD Uncensored (430) → adult
  ├─ AV(无码)/DVDiSo Uncensored (426) → adult
  ├─ AV(无码)/Blu-Ray Uncensored (432) → adult
  └─ AV(网站)/0Day (436) → adult

IV (445) → adult
  ├─ IV(写真影集) (425) → adult
  └─ IV(写真图集) (433) → adult

H-ACG (446) → adult
  ├─ H-游戏 (411) → adult
  ├─ H-动漫 (412) → adult
  └─ H-漫画 (413) → adult
```

---

## 数据库设计

### pt_categories 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| site_id | Integer | 站点ID（外键） |
| category_id | String | 站点内分类ID |
| name_chs | String | 中文简体名称 |
| name_cht | String | 中文繁体名称 |
| name_eng | String | 英文名称 |
| parent_id | String | 父分类ID |
| order | Integer | 排序 |
| image | String | 图标 |
| mapped_category | String | 映射的标准分类 |
| is_adult | Boolean | 是否成人内容 |
| is_active | Boolean | 是否启用 |
| raw_data | JSON | 原始数据 |

**唯一约束**：`(site_id, category_id)`

---

## 最佳实践

### 1. 定期同步

站点分类可能会更新，建议定期同步：

```bash
# 每月同步一次
POST /api/v1/pt-sites/1/sync-categories
```

### 2. 首次同步后检查

同步完成后，检查映射是否准确：

```bash
# 查看所有分类
GET /api/v1/pt-sites/1/categories

# 检查是否有需要调整的映射
```

### 3. 前端展示优化

```javascript
// 按标准分类分组显示
const groupedCategories = categories.reduce((acc, cat) => {
  if (!acc[cat.mapped_category]) {
    acc[cat.mapped_category] = [];
  }
  acc[cat.mapped_category].push(cat);
  return acc;
}, {});
```

### 4. 成人内容管理

```javascript
// 提供开关控制是否显示成人内容
const safeCategories = categories.filter(cat => !cat.is_adult);
```

---

## 故障排查

### 问题1：同步失败

**症状**：POST `/sync-categories` 返回500错误

**排查步骤**：
1. 检查站点API是否可访问
2. 检查API Key是否有效
3. 查看后端日志：`tail -f backend/data/logs/nasfusion.log`

### 问题2：映射不准确

**症状**：某些分类映射到了错误的标准分类

**解决方案**：
```bash
# 手动修正映射
PUT /api/v1/pt-sites/1/categories/{category_id}?mapped_category=正确的分类
```

### 问题3：分类太多

**症状**：某些站点有上百个分类

**建议**：
- 使用树形结构展示
- 前端实现搜索/过滤功能
- 仅显示常用的根分类

---

## 总结

分类管理系统解决了多站点分类不统一的问题：

- ✅ **自动化** - 一键同步，自动映射
- ✅ **灵活性** - 支持手动调整
- ✅ **扩展性** - 易于添加新站点
- ✅ **用户友好** - 统一的分类体系，便于筛选

建议在添加新站点后立即同步分类，并在资源同步时使用分类过滤以提高效率。
