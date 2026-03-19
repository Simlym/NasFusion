# 媒体刮削逻辑说明

本文档详细说明 NasFusion 的媒体刮削（NFO 生成、图片下载）逻辑，包括电影和电视剧的处理流程及数据源优先级。

---

## 目录

- [概述](#概述)
- [电影刮削逻辑](#电影刮削逻辑)
- [电视剧刮削逻辑](#电视剧刮削逻辑)
- [识别优先级配置](#识别优先级配置)
- [TVDB 降级逻辑](#tvdb-降级逻辑)
- [配置说明](#配置说明)

---

## 概述

NasFusion 的刮削流程分为两个阶段：

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   资源识别阶段   │  →   │   UnifiedMovie  │  →   │    刮削阶段     │
│  (调用外部API)   │      │ UnifiedTVSeries │      │ (生成NFO/下载图片)│
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

- **资源识别阶段**：调用豆瓣/TMDB API，将元数据存储到统一资源表
- **刮削阶段**：使用已存储的元数据生成 NFO 文件和下载图片

---

## 电影刮削逻辑

### 架构特点

电影刮削**不会实时调用外部 API**，直接使用 `UnifiedMovie` 表中已存储的数据。

### 数据流

```
UnifiedMovie 表
    ├── title, original_title, year
    ├── tmdb_id, imdb_id, douban_id
    ├── rating_tmdb, rating_imdb, rating_douban
    ├── overview, tagline, genres
    ├── actors, directors, writers
    ├── poster_url  ──────────────→  下载海报
    └── backdrop_url ─────────────→  下载背景图
                 ↓
         _build_movie_xml()
                 ↓
           电影.nfo 文件
```

### NFO 生成内容

电影 NFO 文件包含以下信息：

| 标签 | 数据来源 |
|------|----------|
| `<uniqueid>` | tmdb_id, imdb_id, douban_id |
| `<title>` | UnifiedMovie.title |
| `<originaltitle>` | UnifiedMovie.original_title |
| `<year>` | UnifiedMovie.year |
| `<ratings>` | rating_tmdb, rating_imdb, rating_douban |
| `<plot>` | UnifiedMovie.overview |
| `<genre>` | UnifiedMovie.genres |
| `<actor>` | UnifiedMovie.actors |
| `<director>` | UnifiedMovie.directors |
| `<thumb>` | UnifiedMovie.poster_url |
| `<fanart>` | UnifiedMovie.backdrop_url |

### 相关代码

- NFO 生成：`services/mediafile/nfo_generator_service.py:_generate_movie_nfo()`
- XML 构建：`services/mediafile/nfo_generator_service.py:_build_movie_xml()`
- 图片下载：`services/mediafile/scraper_service.py:scrape_media_file()` (104-142行)

---

## 电视剧刮削逻辑

### 架构特点

电视剧刮削**需要实时调用外部 API** 获取单集详情（标题、简介、剧照等）。

### 数据流

```
UnifiedTVSeries 表
    ├── 基础信息 (title, year, tmdb_id, imdb_id, tvdb_id, douban_id)
    ├── poster_url  ──────────────→  下载剧集海报
    └── backdrop_url ─────────────→  下载背景图
                 ↓
    _fetch_episode_info_with_fallback()  ←── 实时调用 TMDB/TVDB API
                 ↓
    获取单集详情 (name, overview, air_date, still_path, guest_stars)
                 ↓
         _build_tv_episode_xml()
                 ↓
           剧集.nfo 文件
```

### 降级逻辑

电视剧单集信息获取采用多级降级策略：

```
1. 检查是否有 TMDB ID
   ├── 无 → 尝试自动补全 TMDB ID
   │        ├── 通过豆瓣ID获取IMDB ID
   │        ├── 通过IMDB ID调用TMDB find API
   │        └── 通过标题+年份搜索TMDB
   │
2. 使用 TMDB 获取单集信息
   ├── 成功 → 返回结果
   └── 失败 → 继续降级

3. 检查是否有 TVDB ID
   ├── 无 → 尝试通过TMDB获取TVDB ID
   │
4. 使用 TVDB 获取单集信息
   ├── 成功 → 返回结果
   └── 失败 → 返回 None（使用基础信息）
```

### 图片下载层级

电视剧图片按目录层级下载：

```
/TV Shows/
└── 剧名 (2024)/
    ├── poster.jpg      ← 剧集海报 (UnifiedTVSeries.poster_url)
    ├── backdrop.jpg    ← 背景图 (UnifiedTVSeries.backdrop_url)
    └── Season 01/
        ├── poster.jpg  ← 季海报 (TMDB/TVDB season.poster_path)
        ├── S01E01.mkv
        ├── S01E01-thumb.jpg  ← 单集剧照 (episode.still_path)
        ├── S01E01.nfo
        └── ...
```

### 相关代码

- NFO 生成：`services/mediafile/nfo_generator_service.py:_generate_tv_episode_nfo()`
- 降级逻辑：`services/mediafile/nfo_generator_service.py:_fetch_episode_info_with_fallback()`
- TMDB 获取：`services/mediafile/nfo_generator_service.py:_fetch_episode_info_from_tmdb()`
- TVDB 获取：`services/mediafile/nfo_generator_service.py:_fetch_episode_info_from_tvdb()`
- 图片处理：`services/mediafile/scraper_service.py:_process_tv_images()`
- ID 自动补全：`services/mediafile/tmdb_id_resolver_service.py`

---

## 识别优先级配置

### 默认优先级

资源识别阶段的数据源优先级（可在前端配置页面调整）：

| 优先级 | 识别源 | 说明 |
|--------|--------|------|
| 1 | `local_cache` | 本地缓存（最快，0成本） |
| 2 | `mteam_douban` | MTeam 豆瓣接口（准确，免费） |
| 3 | `douban_api` | 豆瓣 API 直接查询（需要 douban_id） |
| 4 | `tmdb_by_imdb` | TMDB 精确匹配（需要 imdb_id） |
| 5 | `douban_search` | 豆瓣搜索（可能不准确） |
| 6 | `tmdb_search` | TMDB 搜索（最后兜底） |

### 配置位置

- 前端：`/settings?tab=media-scraping` → 识别优先级
- 数据库：`system_settings` 表，`category='metadata_scraping'`, `key='identification_priority'`
- 常量定义：`constants/resource_identification.py`

---

## TVDB 降级逻辑

### 触发条件

当以下情况发生时，系统会尝试使用 TVDB：

1. TMDB 无法获取单集信息
2. TMDB API 未配置
3. TMDB API 调用失败

### TMDB ID 自动补全流程

```python
# TMDBIdResolverService.resolve_tmdb_id_for_tv()

1. 如果有豆瓣ID → 调用豆瓣API获取IMDB ID
2. 如果有IMDB ID → 调用TMDB find API获取TMDB ID
3. 如果还是没有 → 使用标题+年份搜索TMDB
4. 成功获取后更新数据库
```

### TVDB ID 自动补全流程

```python
# TMDBIdResolverService.resolve_tvdb_id_for_tv()

1. 如果有TMDB ID → 调用TMDB获取external_ids
2. 从external_ids中提取tvdb_id
3. 成功获取后更新数据库
```

---

## 配置说明

### 数据库配置项

| category | key | 说明 |
|----------|-----|------|
| `metadata_scraping` | `tmdb_api_key` | TMDB API Key（必需） |
| `metadata_scraping` | `tmdb_proxy` | TMDB 代理地址（可选） |
| `metadata_scraping` | `tvdb_api_key` | TVDB API Key（可选） |
| `metadata_scraping` | `tvdb_pin` | TVDB 订阅者 PIN（可选） |
| `metadata_scraping` | `tvdb_proxy` | TVDB 代理地址（可选） |
| `metadata_scraping` | `identification_priority` | 识别优先级配置（JSON） |

### 整理配置（OrganizeConfig）

每个整理规则可以单独配置：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `generate_nfo` | 是否生成 NFO 文件 | `True` |
| `nfo_format` | NFO 格式 (jellyfin/emby/plex/kodi) | `jellyfin` |
| `download_poster` | 是否下载海报 | `True` |
| `download_backdrop` | 是否下载背景图 | `True` |
| `overwrite_nfo` | 覆盖已存在的 NFO | `False` |
| `overwrite_poster` | 覆盖已存在的海报 | `False` |
| `overwrite_backdrop` | 覆盖已存在的背景图 | `False` |

---

## 电影 vs 电视剧对比

| 对比项 | 电影 | 电视剧 |
|--------|------|--------|
| NFO 数据来源 | UnifiedMovie 表 | UnifiedTVSeries + 实时 API |
| 外部 API 调用 | 仅识别阶段 | 识别阶段 + 刮削阶段 |
| 降级逻辑 | 无 | 有（TMDB → TVDB） |
| 图片层级 | 单层（电影目录） | 多层（剧集/季/单集） |
| NFO 类型 | `<movie>` | `<episodedetails>` |

---

## 相关文件

- `backend/app/services/mediafile/scraper_service.py` - 刮削服务主入口
- `backend/app/services/mediafile/nfo_generator_service.py` - NFO 生成服务
- `backend/app/services/mediafile/tmdb_id_resolver_service.py` - TMDB ID 自动补全
- `backend/app/services/identification/resource_identify_service.py` - 资源识别服务
- `backend/app/services/identification/identify_priority_service.py` - 识别优先级配置
- `backend/app/adapters/metadata/tmdb_adapter.py` - TMDB 适配器
- `backend/app/adapters/metadata/tvdb_adapter.py` - TVDB 适配器
- `backend/app/adapters/metadata/douban_adapter.py` - 豆瓣适配器

---

**文档维护者**: Claude Code
**最后更新**: 2025-01-20
**版本**: v1.0
