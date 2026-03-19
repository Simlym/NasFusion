# PT站点媒体资源管理系统 - 完整数据库设计文档

## 目录
1. [数据库表汇总](#1-数据库表汇总)
2. [系统概述](#2-系统概述)
3. [数据库架构总览](#3-数据库架构总览)
4. [详细表结构设计](#4-详细表结构设计)
   - [4.1 核心业务表](#41-核心业务表)
   - [4.2 订阅系统表](#42-订阅系统表)
   - [4.3 用户系统表](#43-用户系统表)
   - [4.4 系统管理表](#44-系统管理表)
   - [4.5 日志系统表](#45-日志系统表)
5. [索引设计策略](#5-索引设计策略)
6. [数据关系和约束](#6-数据关系和约束)
7. [部署和配置建议](#7-部署和配置建议)
8. [扩展性考虑](#8-扩展性考虑)

---

## 1. 数据库表汇总

### 1.1 核心业务表

| 表名 | 用途 | 主要功能 |
|------|------|----------|
| **pt_sites** | PT站点配置 | 存储所有PT站点的认证信息、同步配置和状态监控 |
| **pt_resources** | PT原始资源 | 存储从PT站点爬取的原始种子信息和元数据 |
| **unified_movies** | 统一电影资源 | 电影媒体的统一元数据，支持多站点资源聚合 |
| **unified_tv_series** | 统一剧集资源 | 电视剧系列的统一元数据，包含季集信息 |
| **unified_music** | 统一音乐资源 | 音乐专辑和曲目的统一元数据 |
| **unified_books** | 统一书籍资源 | 电子书和实体书籍的统一元数据 |
| **unified_anime** | 统一动画资源 | 动画作品的统一元数据 |
| **unified_adult** | 统一成人内容资源 | 成人内容媒体作品的统一元数据 |
| **resource_mappings** | 资源关联映射 | PT资源与统一资源的多对一映射关系 |
| **download_tasks** | 下载任务 | 管理所有下载任务的状态和进度 |
| **media_files** | 媒体文件 | 管理磁盘上的所有媒体文件及其处理状态 |

### 1.2 订阅系统表

| 表名 | 用途 | 主要功能 |
|------|------|----------|
| **subscriptions** | 订阅管理 | 用户媒体订阅管理，支持智能匹配和自动下载 |
| **subscription_check_logs** | 订阅检查日志 | 记录订阅检查的历史和结果 |

### 1.3 用户系统表

| 表名 | 用途 | 主要功能 |
|------|------|----------|
| **users** | 用户管理 | 系统用户基础信息管理 |
| **user_profiles** | 用户配置 | 用户个人偏好和系统配置 |
| **notification_channels** | 通知渠道配置 | 配置各种通知渠道（Telegram、邮件、Webhook等） |

### 1.4 系统管理表

| 表名 | 用途 | 主要功能 |
|------|------|----------|
| **system_settings** | 系统配置 | 存储所有用户可配置的系统设置 |
| **scheduled_tasks** | 调度任务模板 | 存储定时任务的调度配置和处理器定义 |
| **task_queue** | 任务队列 | 存储待执行和执行中的任务实例，支持重试和优先级 |

### 1.5 日志系统表

| 表名 | 用途 | 主要功能 |
|------|------|----------|
| **sync_logs** | 同步日志 | 记录PT站点同步任务的详细日志 |
| **organize_logs** | 整理日志 | 记录媒体整理任务的详细日志 |
| **download_logs** | 下载日志/事件 | 记录下载任务的关键事件 |
| **scan_tasks** | 扫描任务记录 | 记录目录扫描任务历史 |
| **notification_logs** | 通知日志 | 记录所有发送的通知 |
| **ai_recommendation_logs** | AI推荐日志 | 记录AI推荐的历史和成本 |

---

## 2. 系统概述

### 2.1 项目简介
本系统是一个以PT站点为核心的媒体资源管理系统，解决传统"先有影评后有资源"模式的痛点。系统直接基于PT站点资源进行数据同步和管理，提供快速、便捷的媒体资源发现、下载、整理和观看体验。

### 2.2 核心理念
- **PT优先**：以PT站点资源为数据起点，而非TMDB/豆瓣等影评平台
- **本地缓存**：定期同步PT站点资源到本地数据库，提供快速检索体验
- **智能推荐**：基于用户观看历史和偏好的AI推荐系统
- **全流程管理**：从资源发现到媒体库入库的完整生命周期管理

### 2.3 技术栈
- **后端框架**：FastAPI + SQLAlchemy
- **前端框架**：Vue3 + TypeScript
- **数据库**：PostgreSQL
- **缓存**：Redis（可选）
- **AI集成**：OpenAI API（支持代理访问）

### 2.4 核心功能模块
1. **PT站点管理**：站点配置、认证、限流、健康检查
2. **资源同步系统**：全量+增量同步，多站点聚合
3. **下载管理**：多下载器支持，任务调度
4. **媒体整理**：自动文件整理、NFO生成、刮削
5. **订阅系统**：媒体状态跟踪、智能匹配
6. **智能推荐**：基于AI的个性化资源推荐
7. **通知系统**：多渠道通知、用户偏好配置

---

## 3. 数据库架构总览

### 3.1 设计原则
- **数据完整性**：通过外键约束确保数据一致性
- **查询性能**：合理的索引设计支持高效查询
- **扩展性**：JSON字段支持灵活的配置扩展
- **可维护性**：详细的日志记录支持问题排查

### 3.2 表关系概览
```
用户系统 (users, user_profiles)
    ↓
pt资源同步 (pt_sites → pt_resources → resource_mappings
→ unified_movies
→ unified_tv_series
→ unified_music
→ unified_books
→ unified_anime
→ unified_adult, sync_logs)
    ↓
下载管理 (download_tasks → media_files(insert), download_logs)
    &
本地文件扫描 (scan_tasks → media_files(insert), scan_logs)
    ↓
整理和刮削 (media_process_tasks → media_files(update), media_process_logs)
    ↓
订阅系统 (subscription_tasks , subscriptions, subscription_logs)
    ↓
AI推荐 (ai_recommend_tasks, ai_recommendation_logs)
    ↓
通知 (notification_channels,notification_logs)
    ↓
系统配置 (system_settings)
```

### 3.3 数据流设计
1. **同步流程**：PT站点 → pt_resources → resource_mappings → unified_resources
2. **订阅流程**：用户订阅 → 定期检查 → 资源匹配 → 通知/下载
3. **下载流程**：资源选择 → 下载任务 → 文件整理 → 媒体入库
4. **推荐流程**：用户画像 → AI分析 → 推荐生成 → 用户反馈

---

## 4. 详细表结构设计

### 4.1 核心业务表

#### 4.1.1 pt_sites（PT站点配置）
**用途**：存储用户配置的所有PT站点信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PK, AUTOINCREMENT | 主键 |
| name | String(100) | NOT NULL | 站点名称（如"MTeam"） |
| type | String(50) | NOT NULL | 站点类型（如"mteam", "chd"，对应爬虫适配器） |
| domain | String(255) | UNIQUE, NOT NULL | 站点域名 |
| base_url | String(500) | NOT NULL | 完整URL |
| auth_type | String(50) | NOT NULL | 认证方式（cookie/passkey/user_pass） |
| auth_cookie | Text |  | Cookie（加密存储） |
| auth_passkey | String(255) |  | Passkey（加密存储） |
| auth_username | String(255) |  | 用户名（加密存储） |
| auth_password | String(255) |  | 密码（加密存储） |
| cookie_expire_at | DateTime |  | Cookie过期时间 |
| proxy_config | JSON |  | JSON，代理配置 |
| capabilities | JSON |  | 站点能力配置 |
| sync_enabled | Boolean | DEFAULT TRUE | 是否启用同步 |
| sync_strategy | String(50) |  | 同步策略（time_based/page_based/id_based） |
| sync_interval | Integer |  | 同步间隔（分钟） |
| sync_config | JSON |  | 同步详细配置 |
| last_sync_at | DateTime |  | 最后同步时间 |
| last_sync_status | String(50) |  | 最后同步状态（success/failed/running） |
| last_sync_error | Text |  | 最后同步错误信息 |
| request_interval | Integer |  | 请求间隔（秒） |
| max_requests_per_day | Integer |  | 每日最大请求数 |
| daily_requests_used | Integer |  | 今日已用请求数 |
| status | String(50) |  | 站点状态（active/inactive/error） |
| health_check_at | DateTime |  | 最后健康检查时间 |
| health_status | String(50) |  | 健康状态（healthy/unhealthy） |
| total_resources | Integer |  | 总资源数 |
| total_synced | Integer |  | 已同步数 |
| created_at | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(domain)`
- `INDEX(status, sync_enabled)`
- `INDEX(type, status)`
- `INDEX(last_sync_at)`
- `INDEX(health_status, health_check_at)`
- `INDEX(auth_type)`

---

#### 4.1.2 pt_resources（PT原始资源）
**用途**：存储从PT站点爬取的原始种子信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| site_id | INTEGER | FK → pt_sites | 站点ID |
| torrent_id | VARCHAR(200) | NOT NULL | 站点内种子ID |
| title | VARCHAR(1000) | NOT NULL | 原始标题 |
| subtitle | VARCHAR(500) |  | 副标题 |
| category | VARCHAR(20) |  | 分类：movie/tv/music/book/other |
| size_bytes | BIGINT | NOT NULL | 文件大小，字节 |
| file_count | INTEGER | DEFAULT 1 | 文件数量 |
| torrent_hash | VARCHAR(40) |  | 种子哈希，InfoHash |
| seeders | INTEGER | DEFAULT 0 | 做种数 |
| leechers | INTEGER | DEFAULT 0 | 下载数 |
| completions | INTEGER | DEFAULT 0 | 完成数 |
| last_seeder_update_at | TIMESTAMP |  | 做种数最后更新时间 |
| promotion_type | VARCHAR(20) |  | 促销类型：free/50%/2x/2x50%/none |
| promotion_expire_at | TIMESTAMP |  | 促销结束时间 |
| is_free | BOOLEAN | DEFAULT FALSE | 快速查询是否免费 |
| is_discount | BOOLEAN | DEFAULT FALSE | 是否折扣 |
| is_double_upload | BOOLEAN | DEFAULT FALSE | 是否双倍上传 |
| has_hr | BOOLEAN | DEFAULT FALSE | 是否有HR要求 |
| hr_days | INTEGER |  | 需要保种天数 |
| hr_seed_time | INTEGER |  | 需要保种小时数 |
| hr_ratio | DECIMAL(5,2) |  | 需要分享率 |
| resolution | VARCHAR(20) |  | 分辨率：2160p/1080p/720p等 |
| source | VARCHAR(50) |  | 来源：BluRay/WEB-DL/HDTV等 |
| codec | VARCHAR(50) |  | 编码：x264/x265/AV1等 |
| audio | JSON |  | 音轨信息，JSON数组 |
| subtitle_info | JSON |  | 字幕信息，JSON数组 |
| quality_tags | JSON |  | 其他质量标签，JSON数组 |
| imdb_id | VARCHAR(20) |  | IMDB ID |
| douban_id | VARCHAR(20) |  | 豆瓣ID |
| tmdb_id | INTEGER |  | TMDB ID |
| detail_url | TEXT |  | 详情页URL |
| download_url | TEXT | NOT NULL | 下载链接 |
| magnet_link | TEXT |  | 磁力链接 |
| raw_page_html | Text |  | 原始页面HTML内容（用于调试和问题排查） |
| raw_page_json | JSON |  | 原始页面解析后的结构化数据 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否有效 |
| last_check_at | TIMESTAMP |  | 最后检查时间 |
| published_at | TIMESTAMP |  | 发布时间 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 入库时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(site_id, torrent_id)`
- `INDEX(site_id, published_at DESC)`
- `INDEX(imdb_id) WHERE imdb_id IS NOT NULL`
- `INDEX(douban_id) WHERE douban_id IS NOT NULL`
- `INDEX(is_free, is_active)`
- `INDEX(category, is_active)`

**字段说明**：
- **raw_page_html**：保存完整的原始HTML页面，用于调试解析问题和数据验证
- **raw_page_json**：保存解析后的结构化数据，便于查询和分析原始信息
- 这两个字段为可选字段，建议根据存储策略选择性保存重要或异常的记录

---

### 4.1.3 统一媒体资源表（按类型拆分）

**设计理念**：为优化查询性能和存储效率，将统一资源表按媒体类型拆分为6个专用表。每个表只包含该类型媒体相关的字段，避免大量NULL值，提升查询效率。

#### 4.1.3.1 unified_movies（电影资源表）
**用途**：存储电影媒体的统一元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| tmdb_id | INTEGER | UNIQUE | TMDB ID |
| imdb_id | VARCHAR(20) | UNIQUE | IMDB ID |
| douban_id | VARCHAR(20) | UNIQUE | 豆瓣ID |
| title_zh | VARCHAR(500) | NOT NULL | 中文标题 |
| title_en | VARCHAR(500) |  | 英文标题 |
| title_original | VARCHAR(500) |  | 原始标题 |
| year | INTEGER |  | 年份 |
| release_date | DATE |  | 上映日期 |
| rating_tmdb | DECIMAL(3,1) |  | TMDB评分 |
| rating_douban | DECIMAL(3,1) |  | 豆瓣评分 |
| rating_imdb | DECIMAL(3,1) |  | IMDB评分 |
| votes_count | INTEGER |  | 投票数 |
| genres | JSON |  | 类型标签，JSON数组 |
| tags | JSON |  | 标签，JSON数组 |
| countries | JSON |  | 制作国家，JSON数组 |
| languages | JSON |  | 语言，JSON数组 |
| directors | JSON |  | 导演，JSON数组 |
| actors | JSON |  | 主演，JSON数组 |
| writers | JSON |  | 编剧，JSON数组 |
| overview | TEXT |  | 简介 |
| overview_zh | TEXT |  | 中文简介 |
| runtime | INTEGER |  | 时长，分钟 |
| budget | BIGINT |  | 预算 |
| revenue | BIGINT |  | 票房 |
| original_language | VARCHAR(10) |  | 原始语言 |
| production_companies | JSON |  | 制作公司，JSON数组 |
| production_countries | JSON |  | 制作国家，JSON数组 |
| status | VARCHAR(20) |  | 状态：Released/Post_Production/Rumored |
| poster_thumb_url | TEXT |  | 海报缩略图 |
| poster_full_url | TEXT |  | 海报完整图 |
| backdrop_url | TEXT |  | 背景图 |
| logo_url | TEXT |  | Logo |
| pt_resource_count | INTEGER | DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | DEFAULT FALSE | 是否有Free资源 |
| best_quality | VARCHAR(20) |  | 最佳质量：4K/1080P等 |
| best_seeder_count | INTEGER | DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP |  | PT资源最后更新时间 |
| local_file_count | INTEGER | DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | DEFAULT FALSE | 是否有本地文件 |
| detail_loaded | BOOLEAN | DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP |  | 详情加载时间 |
| metadata_source | VARCHAR(20) |  | 元数据来源：tmdb/douban/imdb |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(tmdb_id) WHERE tmdb_id IS NOT NULL`
- `UNIQUE(imdb_id) WHERE imdb_id IS NOT NULL`
- `UNIQUE(douban_id) WHERE douban_id IS NOT NULL`
- `INDEX(year DESC, rating_tmdb DESC)`
- `INDEX(has_free_resource, pt_resource_count DESC)`
- `INDEX(release_date DESC)`
- `INDEX(original_language)`

---

#### 3.1.3.2 unified_tv_series（剧集资源表）
**用途**：存储电视剧系列的统一元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| tmdb_id | INTEGER | UNIQUE | TMDB ID |
| tvdb_id | INTEGER | UNIQUE | TVDB ID |
| imdb_id | VARCHAR(20) | UNIQUE | IMDB ID |
| douban_id | VARCHAR(20) | UNIQUE | 豆瓣ID |
| title_zh | VARCHAR(500) | NOT NULL | 中文标题 |
| title_en | VARCHAR(500) |  | 英文标题 |
| title_original | VARCHAR(500) |  | 原始标题 |
| year | INTEGER |  | 年份 |
| first_air_date | DATE |  | 首播日期 |
| last_air_date | DATE |  | 最后播出日期 |
| number_of_seasons | INTEGER |  | 总季数 |
| number_of_episodes | INTEGER |  | 总集数 |
| episode_run_time | INTEGER |  | 单集时长，分钟 |
| rating_tmdb | DECIMAL(3,1) |  | TMDB评分 |
| rating_douban | DECIMAL(3,1) |  | 豆瓣评分 |
| rating_imdb | DECIMAL(3,1) |  | IMDB评分 |
| votes_count | INTEGER |  | 投票数 |
| genres | JSON |  | 类型标签，JSON数组 |
| tags | JSON |  | 标签，JSON数组 |
| countries | JSON |  | 制作国家，JSON数组 |
| languages | JSON |  | 语言，JSON数组 |
| creators | JSON |  | 创作者，JSON数组 |
| directors | JSON |  | 导演，JSON数组 |
| actors | JSON |  | 主演，JSON数组 |
| writers | JSON |  | 编剧，JSON数组 |
| overview | TEXT |  | 简介 |
| overview_zh | TEXT |  | 中文简介 |
| status | VARCHAR(20) |  | 状态：Returning Series/Ended/Canceled |
| networks | JSON |  | 播出网络，JSON数组 |
| production_companies | JSON |  | 制作公司，JSON数组 |
| seasons | JSON |  | 季度信息，JSON数组 |
| poster_thumb_url | TEXT |  | 海报缩略图 |
| poster_full_url | TEXT |  | 海报完整图 |
| backdrop_url | TEXT |  | 背景图 |
| logo_url | TEXT |  | Logo |
| pt_resource_count | INTEGER | DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | DEFAULT FALSE | 是否有Free资源 |
| best_quality | VARCHAR(20) |  | 最佳质量：4K/1080P等 |
| best_seeder_count | INTEGER | DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP |  | PT资源最后更新时间 |
| local_file_count | INTEGER | DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | DEFAULT FALSE | 是否有本地文件 |
| detail_loaded | BOOLEAN | DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP |  | 详情加载时间 |
| metadata_source | VARCHAR(20) |  | 元数据来源：tmdb/douban/imdb |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(tmdb_id) WHERE tmdb_id IS NOT NULL`
- `UNIQUE(tvdb_id) WHERE tvdb_id IS NOT NULL`
- `UNIQUE(imdb_id) WHERE imdb_id IS NOT NULL`
- `UNIQUE(douban_id) WHERE douban_id IS NOT NULL`
- `INDEX(first_air_date DESC, rating_tmdb DESC)`
- `INDEX(status, number_of_seasons)`
- `INDEX(has_free_resource, pt_resource_count DESC)`

---

#### 3.1.3.3 unified_music（音乐资源表）
**用途**：存储音乐专辑和曲目的统一元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| musicbrainz_id | VARCHAR(100) | UNIQUE | MusicBrainz ID |
| title_zh | VARCHAR(500) | NOT NULL | 中文标题 |
| title_en | VARCHAR(500) |  | 英文标题 |
| title_original | VARCHAR(500) |  | 原始标题 |
| artist_name | VARCHAR(500) | NOT NULL | 艺术家名 |
| album_name | VARCHAR(500) |  | 专辑名 |
| track_number | INTEGER |  | 曲目编号 |
| disc_number | INTEGER | DEFAULT 1 | 光盘编号 |
| duration_ms | INTEGER |  | 时长，毫秒 |
| year | INTEGER |  | 年份 |
| release_date | DATE |  | 发行日期 |
| release_type | VARCHAR(20) |  | 发行类型：Album/Single/EP |
| genres | JSON |  | 音乐类型，JSON数组 |
| tags | JSON |  | 标签，JSON数组 |
| countries | JSON |  | 发行国家，JSON数组 |
| languages | JSON |  | 语言，JSON数组 |
| composers | JSON |  | 作曲家，JSON数组 |
| lyricists | JSON |  | 作词家，JSON数组 |
| producers | JSON |  | 制作人，JSON数组 |
| explicit | BOOLEAN | DEFAULT FALSE | 是否显式内容 |
| isrc | VARCHAR(12) |  | 国际标准录音代码 |
| overview | TEXT |  | 简介 |
| overview_zh | TEXT |  | 中文简介 |
| record_label | VARCHAR(200) |  | 唱片公司 |
| copyright | TEXT |  | 版权信息 |
| poster_thumb_url | TEXT |  | 专辑封面缩略图 |
| poster_full_url | TEXT |  | 专辑封面完整图 |
| pt_resource_count | INTEGER | DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | DEFAULT FALSE | 是否有Free资源 |
| best_quality | VARCHAR(20) |  | 最佳质量：FLAC/MP3等 |
| best_seeder_count | INTEGER | DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP |  | PT资源最后更新时间 |
| local_file_count | INTEGER | DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | DEFAULT FALSE | 是否有本地文件 |
| detail_loaded | BOOLEAN | DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP |  | 详情加载时间 |
| metadata_source | VARCHAR(20) |  | 元数据来源：musicbrainz/spotify |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(musicbrainz_id) WHERE musicbrainz_id IS NOT NULL`
- `UNIQUE(isrc) WHERE isrc IS NOT NULL`
- `INDEX(artist_name, release_date DESC)`
- `INDEX(album_name, track_number)`
- `INDEX(release_type, year DESC)`
- `INDEX(explicit, duration_ms)`
- `INDEX(has_free_resource, pt_resource_count DESC)`

---

#### 3.1.3.4 unified_books（书籍资源表）
**用途**：存储电子书和实体书籍的统一元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| isbn | VARCHAR(20) | UNIQUE | ISBN-13 |
| isbn10 | VARCHAR(10) | UNIQUE | ISBN-10 |
| douban_id | VARCHAR(20) | UNIQUE | 豆瓣ID |
| title_zh | VARCHAR(500) | NOT NULL | 中文标题 |
| title_en | VARCHAR(500) |  | 英文标题 |
| title_original | VARCHAR(500) |  | 原始标题 |
| authors | JSON |  | 作者列表，JSON数组 |
| publisher | VARCHAR(500) |  | 出版社 |
| publication_date | DATE |  | 出版日期 |
| page_count | INTEGER |  | 页数 |
| language | VARCHAR(10) |  | 语言 |
| format | VARCHAR(20) |  | 格式：Hardcover/Paperback/eBook/Audiobook |
| edition | VARCHAR(100) |  | 版本 |
| series_name | VARCHAR(500) |  | 系列名 |
| series_index | INTEGER |  | 系列中的序号 |
| genres | JSON |  | 类型标签，JSON数组 |
| tags | JSON |  | 标签，JSON数组 |
| countries | JSON |  | 出版国家，JSON数组 |
| translators | JSON |  | 译者，JSON数组 |
| overview | TEXT |  | 简介 |
| overview_zh | TEXT |  | 中文简介 |
| rating_douban | DECIMAL(3,1) |  | 豆瓣评分 |
| rating_goodreads | DECIMAL(3,1) |  | Goodreads评分 |
| votes_count | INTEGER |  | 投票数 |
| poster_thumb_url | TEXT |  | 封面缩略图 |
| poster_full_url | TEXT |  | 封面完整图 |
| pt_resource_count | INTEGER | DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | DEFAULT FALSE | 是否有Free资源 |
| best_quality | VARCHAR(20) |  | 最佳质量：EPUB/PDF等 |
| best_seeder_count | INTEGER | DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP |  | PT资源最后更新时间 |
| local_file_count | INTEGER | DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | DEFAULT FALSE | 是否有本地文件 |
| detail_loaded | BOOLEAN | DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP |  | 详情加载时间 |
| metadata_source | VARCHAR(20) |  | 元数据来源：douban/goodreads |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(isbn) WHERE isbn IS NOT NULL`
- `UNIQUE(isbn10) WHERE isbn10 IS NOT NULL`
- `UNIQUE(douban_id) WHERE douban_id IS NOT NULL`
- `INDEX(authors) WHERE authors IS NOT NULL`
- `INDEX(publisher, publication_date DESC)`
- `INDEX(series_name, series_index)`
- `INDEX(language, format)`
- `INDEX(has_free_resource, pt_resource_count DESC)`

---

#### 3.1.3.5 unified_anime（动画资源表）
**用途**：存储动画作品的统一元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| anilist_id | INTEGER | UNIQUE | Anilist ID |
| myanimelist_id | INTEGER | UNIQUE | MyAnimeList ID |
| title_zh | VARCHAR(500) | NOT NULL | 中文标题 |
| title_en | VARCHAR(500) |  | 英文标题 |
| title_jp | VARCHAR(500) |  | 日文标题 |
| title_synonyms | JSON |  | 同名标题，JSON数组 |
| type | VARCHAR(20) |  | 类型：TV/Movie/OVA/ONA/Special |
| source | VARCHAR(50) |  | 原作类型：Manga/Light Novel/Game/Original |
| episodes | INTEGER |  | 集数 |
| duration | INTEGER |  | 单集时长，分钟 |
| rating | VARCHAR(20) |  | 年龄分级：G/PG13/R17+/R+ |
| season | VARCHAR(20) |  | 季度：Spring/Summer/Fall/Winter |
| year | INTEGER |  | 年份 |
| start_date | DATE |  | 开始日期 |
| end_date | DATE |  | 结束日期 |
| studios | JSON |  | 制作公司，JSON数组 |
| producers | JSON |  | 制作委员会，JSON数组 |
| licensors | JSON |  | 授权方，JSON数组 |
| genres | JSON |  | 类型标签，JSON数组 |
| themes | JSON |  | 主题标签，JSON数组 |
| demographics | JSON |  | 目标群体，JSON数组 |
| voice_actors | JSON |  | 声优信息，JSON数组 |
| staff | JSON |  | 制作人员，JSON数组 |
| related_anime | JSON |  | 相关动画，JSON数组 |
| opening_themes | JSON |  | OP主题，JSON数组 |
| ending_themes | JSON |  | ED主题，JSON数组 |
| overview | TEXT |  | 简介 |
| overview_zh | TEXT |  | 中文简介 |
| rating_anilist | DECIMAL(3,1) |  | Anilist评分 |
| rating_myanimelist | DECIMAL(3,1) |  | MyAnimeList评分 |
| votes_count | INTEGER |  | 投票数 |
| popularity_rank | INTEGER |  | 人气排名 |
| members_count | INTEGER |  | 成员数 |
| favorites_count | INTEGER |  | 收藏数 |
| poster_thumb_url | TEXT |  | 封面缩略图 |
| poster_full_url | TEXT |  | 封面完整图 |
| banner_url | TEXT |  | 横幅图片 |
| pt_resource_count | INTEGER | DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | DEFAULT FALSE | 是否有Free资源 |
| best_quality | VARCHAR(20) |  | 最佳质量：4K/1080P等 |
| best_seeder_count | INTEGER | DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP |  | PT资源最后更新时间 |
| local_file_count | INTEGER | DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | DEFAULT FALSE | 是否有本地文件 |
| detail_loaded | BOOLEAN | DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP |  | 详情加载时间 |
| metadata_source | VARCHAR(20) |  | 元数据来源：anilist/myanimelist |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(anilist_id) WHERE anilist_id IS NOT NULL`
- `UNIQUE(myanimelist_id) WHERE myanimelist_id IS NOT NULL`
- `INDEX(season, year DESC, rating_anilist DESC)`
- `INDEX(type, episodes)`
- `INDEX(studios) WHERE studios IS NOT NULL`
- `INDEX(source, start_date DESC)`
- `INDEX(has_free_resource, pt_resource_count DESC)`
- `INDEX(popularity_rank)`

---

#### 3.1.3.6 unified_adult（成人内容资源表）
**用途**：存储成人内容媒体作品的统一元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| title_zh | VARCHAR(500) | NOT NULL | 中文标题 |
| title_en | VARCHAR(500) |  | 英文标题 |
| title_original | VARCHAR(500) |  | 原始标题 |
| year | INTEGER |  | 年份 |
| release_date | DATE |  | 发布日期 |
| duration | INTEGER |  | 时长，分钟 |
| age_rating | VARCHAR(20) |  | 年龄分级 |
| content_warning | JSON |  | 内容警告，JSON数组 |
| production_type | VARCHAR(50) |  | 制作类型 |
| studios | JSON |  | 制作公司，JSON数组 |
| performers | JSON |  | 表演者信息，JSON数组 |
| directors | JSON |  | 导演，JSON数组 |
| categories | JSON |  | 成人内容分类，JSON数组 |
| tags | JSON |  | 标签，JSON数组 |
| countries | JSON |  | 制作国家，JSON数组 |
| languages | JSON |  | 语言，JSON数组 |
| overview | TEXT |  | 简介 |
| overview_zh | TEXT |  | 中文简介 |
| rating | DECIMAL(3,1) |  | 评分 |
| votes_count | INTEGER |  | 投票数 |
| poster_thumb_url | TEXT |  | 封面缩略图 |
| poster_full_url | TEXT |  | 封面完整图 |
| backdrop_url | TEXT |  | 背景图 |
| pt_resource_count | INTEGER | DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | DEFAULT FALSE | 是否有Free资源 |
| best_quality | VARCHAR(20) |  | 最佳质量：4K/1080P等 |
| best_seeder_count | INTEGER | DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP |  | PT资源最后更新时间 |
| local_file_count | INTEGER | DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | DEFAULT FALSE | 是否有本地文件 |
| detail_loaded | BOOLEAN | DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP |  | 详情加载时间 |
| metadata_source | VARCHAR(20) |  | 元数据来源 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `INDEX(year DESC, rating DESC)`
- `INDEX(production_type, release_date DESC)`
- `INDEX(studios) WHERE studios IS NOT NULL`
- `INDEX(categories) WHERE categories IS NOT NULL`
- `INDEX(age_rating)`
- `INDEX(has_free_resource, pt_resource_count DESC)`

---


#### 3.1.4 resource_mappings（资源关联映射）
**用途**：PT原始资源与统一资源的多对一映射关系

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| pt_resource_id | INTEGER | FK → pt_resources, UNIQUE | PT资源ID |
| media_type | VARCHAR(20) | NOT NULL | 媒体类型：movie/tv/music/book/anime/adult |
| unified_table_name | VARCHAR(30) |  | 对应的统一资源表名：unified_movies/unified_tv_series/unified_music/unified_books/unified_anime/unified_adult |
| unified_resource_id | INTEGER |  | 通用外键，指向对应表的ID |
| match_method | VARCHAR(20) |  | 匹配方式：id_exact/title_year/title_fuzzy/manual |
| match_confidence | INTEGER | CHECK (0-100) | 匹配置信度 |
| match_score_detail | JSON |  | 匹配得分详情，JSON |
| is_primary | BOOLEAN | DEFAULT FALSE | 是否主推荐资源 |
| recommendation_score | INTEGER | CHECK (0-100) | 推荐度评分 |
| recommendation_reason | JSON |  | 推荐理由，JSON |
| is_verified | BOOLEAN | DEFAULT FALSE | 是否人工确认 |
| verified_by | INTEGER |  | 确认者 |
| verified_at | TIMESTAMP |  | 确认时间 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(pt_resource_id)`
- `INDEX(unified_table_name, unified_resource_id)`
- `INDEX(unified_table_name, is_primary)`
- `INDEX(media_type, is_primary)`
- `INDEX(match_confidence DESC)`
- `INDEX(media_type, match_method)`



#### 3.1.5 download_tasks（下载任务）
**用途**：管理所有下载任务

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| task_hash | VARCHAR(100) | UNIQUE | 种子哈希，唯一 |
| pt_resource_id | INTEGER | FK → pt_resources | PT资源ID |
| media_type | VARCHAR(20) | NOT NULL | 媒体类型：movie/tv/music/book/anime/adult |
| unified_table_name | VARCHAR(30) |  | 对应的统一资源表名：unified_movies/unified_tv_series/unified_music/unified_books/unified_anime/unified_adult |
| unified_resource_id | INTEGER |  | 通用外键，指向对应表的ID |
| client_type | VARCHAR(50) |  | 下载器类型：qbittorrent/transmission/synology |
| client_id | VARCHAR(100) |  | 下载器任务ID |
| client_config | JSON |  | 下载器配置快照，JSON |
| torrent_file_path | TEXT |  | 种子文件路径 |
| magnet_link | TEXT |  | 磁力链接 |
| torrent_name | VARCHAR(500) |  | 任务名称 |
| save_path | TEXT |  | 保存路径 |
| download_dir | TEXT |  | 下载目录 |
| status | VARCHAR(20) |  | 状态：pending/downloading/paused/completed/seeding/error/deleted |
| progress | INTEGER | CHECK (0-100) | 进度 0-100 |
| download_speed | BIGINT |  | 下载速度，字节/秒 |
| upload_speed | BIGINT |  | 上传速度 |
| eta | INTEGER |  | 预计剩余时间，秒 |
| total_size | BIGINT |  | 总大小，字节 |
| downloaded_size | BIGINT |  | 已下载大小 |
| uploaded_size | BIGINT |  | 已上传大小 |
| ratio | DECIMAL(8,2) |  | 分享率 |
| files | JSON |  | 文件列表，JSON |
| metadata_snapshot | JSON |  | 元数据快照，JSON |
| auto_organize | BOOLEAN | DEFAULT TRUE | 下载完成后是否自动整理 |
| keep_seeding | BOOLEAN | DEFAULT TRUE | 是否保持做种 |
| seeding_time_limit | INTEGER |  | 做种时长限制，小时 |
| seeding_ratio_limit | DECIMAL(5,2) |  | 做种分享率限制 |
| added_at | TIMESTAMP |  | 添加时间 |
| started_at | TIMESTAMP |  | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| error_message | TEXT |  | 错误信息 |
| error_at | TIMESTAMP |  | 错误时间 |
| retry_count | INTEGER | DEFAULT 0 | 重试次数 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(task_hash)`
- `INDEX(status, completed_at DESC)`
- `INDEX(unified_table_name, unified_resource_id)`
- `INDEX(media_type, unified_resource_id)`
- `INDEX(client_type, client_id)`
- `INDEX(pt_resource_id)`



#### 3.1.6 media_files（媒体文件）
**用途**：管理磁盘上的所有媒体文件

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| file_path | TEXT | UNIQUE | 完整路径 |
| file_name | VARCHAR(500) |  | 文件名 |
| directory | TEXT |  | 所属目录 |
| file_size | BIGINT |  | 文件大小，字节 |
| file_hash | VARCHAR(64) |  | SHA256，可选 |
| file_type | VARCHAR(20) |  | 文件类型：video/audio/subtitle/other |
| extension | VARCHAR(10) |  | 扩展名 |
| modified_at | TIMESTAMP |  | 文件修改时间 |
| media_type | VARCHAR(20) |  | 媒体类型：movie/tv/music/book/anime/adult/unknown |
| is_extra | BOOLEAN | DEFAULT FALSE | 是否附加内容：花絮/预告片等 |
| source_type | VARCHAR(20) |  | 来源：download_task/scan/manual |
| source_id | INTEGER |  | 来源ID |
| scan_task_id | INTEGER |  | 扫描任务ID |
| download_task_id | INTEGER | FK → download_tasks | 关联的下载任务ID |
| unified_table_name | VARCHAR(30) |  | 对应的统一资源表名：unified_movies/unified_tv_series/unified_music/unified_books/unified_anime/unified_adult |
| unified_resource_id | INTEGER |  | 通用外键，指向对应表的ID |
| match_method | VARCHAR(20) |  | 识别方式：from_download/from_pt_title/from_filename/from_mediainfo/manual/none |
| match_confidence | INTEGER | CHECK (0-100) | 匹配置信度 |
| match_attempts | INTEGER | DEFAULT 0 | 尝试识别次数 |
| last_match_attempt_at | TIMESTAMP |  | 最后尝试时间 |
| season_number | INTEGER |  | 季号（剧集） |
| episode_number | INTEGER |  | 集号（剧集） |
| episode_title | VARCHAR(500) |  | 集标题（剧集） |
| status | VARCHAR(20) |  | 主状态：discovered/identifying/identified/organizing/scraping/completed/failed/ignored |
| sub_status | JSON |  | 详细状态，JSON |
| organized | BOOLEAN | DEFAULT FALSE | 是否已整理 |
| organized_path | TEXT |  | 整理后路径 |
| organized_at | TIMESTAMP |  | 整理时间 |
| organize_method | VARCHAR(20) |  | 整理方式：auto/manual |
| resolution | VARCHAR(20) |  | 分辨率 |
| width | INTEGER |  | 宽度 |
| height | INTEGER |  | 高度 |
| codec_video | VARCHAR(50) |  | 视频编码 |
| codec_audio | VARCHAR(50) |  | 音频编码 |
| bitrate_video | INTEGER |  | 视频码率 |
| bitrate_audio | INTEGER |  | 音频码率 |
| duration | INTEGER |  | 时长，秒 |
| fps | DECIMAL(5,2) |  | 帧率 |
| audio_channels | INTEGER |  | 声道数 |
| audio_tracks | JSON |  | 音轨列表，JSON |
| subtitle_tracks | JSON |  | 字幕列表，JSON |
| mediainfo_full | TEXT |  | 完整MediaInfo数据，JSON |
| has_nfo | BOOLEAN | DEFAULT FALSE | 是否有NFO文件 |
| nfo_path | TEXT |  | NFO文件路径 |
| nfo_generated_at | TIMESTAMP |  | NFO生成时间 |
| has_poster | BOOLEAN | DEFAULT FALSE | 是否有海报 |
| poster_path | TEXT |  | 海报路径 |
| has_backdrop | BOOLEAN | DEFAULT FALSE | 是否有背景图 |
| backdrop_path | TEXT |  | 背景图路径 |
| scraped_at | TIMESTAMP |  | 刮削时间 |
| has_subtitle | BOOLEAN | DEFAULT FALSE | 是否有字幕 |
| subtitle_paths | JSON |  | 字幕文件路径，JSON数组 |
| subtitle_languages | JSON |  | 字幕语言，JSON数组 |
| subtitle_downloaded_at | TIMESTAMP |  | 字幕下载时间 |
| jellyfin_synced | BOOLEAN | DEFAULT FALSE | 是否已同步到Jellyfin |
| jellyfin_item_id | VARCHAR(100) |  | Jellyfin中的ItemID |
| jellyfin_synced_at | TIMESTAMP |  | 同步时间 |
| discovered_at | TIMESTAMP |  | 发现时间 |
| error_message | TEXT |  | 错误信息 |
| error_at | TIMESTAMP |  | 错误时间 |
| error_step | VARCHAR(50) |  | 失败步骤 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(file_path)`
- `INDEX(file_hash) WHERE file_hash IS NOT NULL`
- `INDEX(unified_table_name, unified_resource_id)`
- `INDEX(media_type, unified_resource_id)`
- `INDEX(download_task_id)`
- `INDEX(status, discovered_at DESC)`
- `INDEX(media_type, status)`
- `INDEX(directory)`


### 4.2 订阅系统表

#### 3.2.1 subscriptions（订阅管理）
**用途**：用户媒体订阅管理

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, NOT NULL DEFAULT 1 | 用户ID |
| media_type | VARCHAR(20) | NOT NULL | 媒体类型：movie/tv/music/book/anime/adult |
| unified_table_name | VARCHAR(30) |  | 对应的统一资源表名：unified_movies/unified_tv_series/unified_music/unified_books/unified_anime/unified_adult |
| unified_resource_id | INTEGER |  | 通用外键，指向对应表的ID |
| douban_id | INTEGER |  | 豆瓣ID，可选 |
| imdb_id | VARCHAR(20) |  | IMDB ID，可选 |
| source | VARCHAR(20) |  | 订阅来源：from_tmdb/from_pt_resource/manual |
| media_status | VARCHAR(20) |  | 媒体状态：announced/in_production/post_production/released/available |
| release_date | DATE |  | 上映/发行日期，来自TMDB |
| days_until_release | INTEGER |  | 距离上映天数，计算字段 |
| subscription_type | VARCHAR(20) |  | 订阅类型：movie_release/tv_episode/tv_season/movie_upgrade |
| has_resources | BOOLEAN | DEFAULT FALSE | 当前是否有PT资源 |
| first_resource_found_at | TIMESTAMP |  | 首次发现资源时间 |
| resource_count | INTEGER | DEFAULT 0 | 当前资源数量 |
| best_resource_quality | VARCHAR(20) |  | 当前最佳资源质量 |
| rules | JSON |  | 订阅规则，JSON |
| status | VARCHAR(20) | DEFAULT 'active' | 订阅状态：active/paused/completed/cancelled |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| check_interval | INTEGER | DEFAULT 360 | 检查间隔，分钟 |
| check_strategy | VARCHAR(20) | DEFAULT 'normal' | 检查策略：aggressive/normal/relaxed |
| last_check_at | TIMESTAMP |  | 最后检查时间 |
| next_check_at | TIMESTAMP |  | 下次检查时间 |
| auto_complete_on_download | BOOLEAN | DEFAULT FALSE | 下载后自动完成 |
| complete_condition | VARCHAR(20) | DEFAULT 'first_match' | 完成条件：first_match/best_quality/manual |
| current_season | INTEGER |  | 当前季（剧集） |
| current_episode | INTEGER |  | 当前集（剧集） |
| track_all_seasons | BOOLEAN | DEFAULT FALSE | 是否追踪所有季 |
| auto_new_season | BOOLEAN | DEFAULT FALSE | 自动新季 |
| notify_on_match | BOOLEAN | DEFAULT TRUE | 匹配时通知 |
| notify_on_download | BOOLEAN | DEFAULT TRUE | 下载时通知 |
| notification_channels | JSON |  | 通知渠道，JSON |
| title | VARCHAR(500) | NOT NULL | 订阅标题 |
| original_title | VARCHAR(500) |  | 原始标题 |
| year | INTEGER |  | 年份 |
| poster_url | TEXT |  | 海报URL |
| user_tags | JSON |  | 用户标签 |
| user_priority | INTEGER | DEFAULT 5 | 用户优先级 |
| user_notes | TEXT |  | 用户备注 |
| is_favorite | BOOLEAN | DEFAULT FALSE | 是否收藏 |
| preferred_regions | JSON |  | 偏好地区 |
| preferred_languages | JSON |  | 偏好语言 |
| require_subtitle | BOOLEAN | DEFAULT FALSE | 是否需要字幕 |
| expected_quality | JSON |  | 期望质量 |
| upgrade_threshold | JSON |  | 升级阈值 |
| ai_matching_enabled | BOOLEAN | DEFAULT FALSE | 启用AI匹配 |
| matching_algorithm | VARCHAR(50) | DEFAULT 'rule_based' | 匹配算法 |
| max_file_size_gb | DECIMAL(8,2) |  | 最大文件大小限制 |
| total_checks | INTEGER | DEFAULT 0 | 总检查次数 |
| total_matches | INTEGER | DEFAULT 0 | 总匹配次数 |
| total_downloads | INTEGER | DEFAULT 0 | 总下载数 |
| average_match_quality | DECIMAL(5,2) |  | 平均匹配质量 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| completed_at | TIMESTAMP |  | 完成时间 |

**索引设计**：
- `INDEX(tmdb_id, media_type)`
- `INDEX(status, is_active, next_check_at)`
- `INDEX(media_status)`
- `INDEX(subscription_type)`
- `INDEX(user_id, tmdb_id, media_type)`

---

#### 3.2.2 subscription_check_logs（订阅检查日志）
**用途**：记录订阅检查的历史和结果

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| subscription_id | INTEGER | FK → subscriptions | 订阅ID |
| check_at | TIMESTAMP | NOT NULL | 检查时间 |
| check_type | VARCHAR(20) |  | 检查类型: tmdb_status/pt_search/both |
| tmdb_status | VARCHAR(50) |  | TMDB返回的状态 |
| tmdb_release_date | DATE |  | TMDB上映日期 |
| tmdb_updated | BOOLEAN |  | TMDB信息是否有更新 |
| sites_searched | INTEGER |  | 搜索的站点数 |
| resources_found | INTEGER |  | 发现的资源数 |
| match_count | INTEGER |  | 匹配规则的资源数 |
| best_match | JSON |  | 最佳匹配资源，JSON |
| action_triggered | VARCHAR(20) |  | 触发的动作: notification/download/none |
| action_detail | JSON |  | 动作详情，JSON |
| execution_time | INTEGER |  | 执行耗时，秒 |
| success | BOOLEAN |  | 是否成功 |
| error_message | TEXT |  | 错误信息 |
| check_environment | JSON |  | 检查环境信息 |
| tmdb_details | JSON |  | TMDB详细信息 |
| search_results | JSON |  | 搜索结果详情 |
| matching_analysis | JSON |  | 匹配分析结果 |
| performance_metrics | JSON |  | 性能指标 |
| decision_process | JSON |  | 决策过程记录 |
| ai_analysis | JSON |  | AI分析结果 |
| follow_up_actions | JSON |  | 后续动作 |
| error_category | VARCHAR(50) |  | 错误分类 |
| error_severity | VARCHAR(20) | DEFAULT 'medium' | 错误严重程度 |
| recovery_action | JSON |  | 恢复动作 |
| learning_data | JSON |  | 机器学习数据 |
| batch_id | VARCHAR(50) |  | 批量检查ID |
| batch_total | INTEGER |  | 批量总数 |
| batch_position | INTEGER |  | 当前位置 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(subscription_id, check_at DESC)`
- `INDEX(check_at DESC)`
- `INDEX(check_type, success)`
- `INDEX(batch_id)`

---

### 4.3 用户系统表

#### 3.3.1 users（用户管理）
**用途**：系统用户基础信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(255) | UNIQUE | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| role | VARCHAR(20) | DEFAULT 'user' | 角色：admin/user |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| is_verified | BOOLEAN | DEFAULT FALSE | 是否已验证 |
| last_login_at | TIMESTAMP |  | 最后登录时间 |
| display_name | VARCHAR(100) |  | 显示名称 |
| avatar_url | TEXT |  | 头像URL |
| timezone | VARCHAR(50) | DEFAULT 'UTC' | 时区 |
| language | VARCHAR(10) | DEFAULT 'zh-CN' | 语言 |
| password_changed_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 密码修改时间 |
| login_attempts | INTEGER | DEFAULT 0 | 登录尝试次数 |
| locked_until | TIMESTAMP |  | 锁定到期时间 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(username)`
- `UNIQUE(email)`
- `INDEX(role, is_active)`
- `INDEX(last_login_at DESC)`

---

#### 3.3.2 user_profiles（用户配置）
**用途**：用户个人偏好和配置

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users, UNIQUE | 用户ID |
| ui_theme | VARCHAR(20) | DEFAULT 'auto' | 界面主题：light/dark/auto |
| language | VARCHAR(10) | DEFAULT 'zh-CN' | 用户界面语言 |
| timezone | VARCHAR(50) | DEFAULT 'UTC' | 用户时区 |
| items_per_page | INTEGER | DEFAULT 50 | 每页显示数量 |
| preferred_quality | JSON |  | 偏好质量设置 |
| min_seeders | INTEGER | DEFAULT 1 | 最小做种数要求 |
| max_auto_download_size_gb | DECIMAL(8,2) |  | 自动下载最大大小(GB) |
| default_downloader | VARCHAR(50) |  | 默认下载器 |
| auto_start_download | BOOLEAN | DEFAULT TRUE | 自动开始下载 |
| download_path_template | TEXT |  | 下载路径模板 |
| notification_enabled | BOOLEAN | DEFAULT TRUE | 启用通知 |
| email_notifications | BOOLEAN | DEFAULT FALSE | 邮件通知 |
| push_notifications | BOOLEAN | DEFAULT TRUE | 推送通知 |
| share_anonymous_stats | BOOLEAN | DEFAULT TRUE | 分享匿名统计 |
| public_watchlist | BOOLEAN | DEFAULT FALSE | 公开观看列表 |
| ai_recommendations_enabled | BOOLEAN | DEFAULT FALSE | AI推荐开关 |
| recommendation_frequency | VARCHAR(20) | DEFAULT 'daily' | 推荐频率 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(user_id)`
- `INDEX(ai_recommendations_enabled)`

---

#### 3.3.3 notification_channels（通知渠道配置）
**用途**：配置各种通知渠道

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| user_id | INTEGER | FK → users | 用户ID，NULL表示系统级 |
| channel_type | VARCHAR(30) | NOT NULL | 渠道类型：telegram/email/webhook/discord |
| name | VARCHAR(100) | NOT NULL | 渠道名称 |
| config | JSON | NOT NULL | 渠道特定配置，JSON |
| enabled | BOOLEAN | DEFAULT TRUE | 是否启用 |
| status | VARCHAR(20) | DEFAULT 'healthy' | 状态：healthy/error |
| last_test_at | TIMESTAMP |  | 最后测试时间 |
| last_test_result | TEXT |  | 最后测试结果 |
| subscribed_events | JSON |  | 订阅的事件类型，JSON数组 |
| priority | INTEGER | DEFAULT 5 CHECK (priority BETWEEN 1 AND 10) | 渠道优先级 |
| rate_limit | JSON |  | 发送频率限制 |
| supports_html | BOOLEAN | DEFAULT FALSE | 是否支持HTML格式 |
| supports_markdown | BOOLEAN | DEFAULT FALSE | 是否支持Markdown格式 |
| max_message_length | INTEGER | DEFAULT 1000 | 最大消息长度 |
| message_templates | JSON |  | 消息模板 |
| failure_handling | JSON |  | 失败处理策略 |
| last_success_at | TIMESTAMP |  | 最后成功时间 |
| consecutive_failures | INTEGER | DEFAULT 0 | 连续失败次数 |
| health_check_url | TEXT |  | 健康检查URL |
| description | TEXT |  | 渠道描述 |
| icon_url | TEXT |  | 图标URL |
| color | VARCHAR(7) | DEFAULT '#007bff' | 渠道颜色 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `INDEX(user_id, name)`
- `UNIQUE(user_id, name)`
- `INDEX(enabled, channel_type)`
- `INDEX(status)`

---

### 4.4 系统管理表

#### 3.4.1 system_settings（系统配置）
**用途**：存储所有用户可配置的系统设置

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| key | VARCHAR(100) | UNIQUE, NOT NULL | 配置键 |
| value | TEXT |  | JSON格式值 |
| value_type | VARCHAR(20) | DEFAULT 'json' | 值类型：json/string/integer/boolean/float |
| category | VARCHAR(30) | NOT NULL | 分类：recommendation/sync/organizer/downloader/notification/ai/jellyfin/general |
| subcategory | VARCHAR(30) |  | 子分类 |
| description | TEXT |  | 配置说明 |
| is_user_configurable | BOOLEAN | DEFAULT TRUE | 是否允许用户修改 |
| is_sensitive | BOOLEAN | DEFAULT FALSE | 是否敏感信息，如API Key |
| default_value | TEXT |  | 默认值，JSON |
| validation_rules | JSON |  | 验证规则，JSON |
| ui_component | VARCHAR(30) |  | UI组件类型：slider/input/select/switch等 |
| ui_options | JSON |  | UI选项，JSON |
| version | VARCHAR(20) | DEFAULT '1.0' | 配置版本 |
| config_schema_version | VARCHAR(20) |  | 配置模式版本 |
| migration_history | JSON |  | 迁移历史 |
| environment | VARCHAR(20) | DEFAULT 'production' | 环境：development/staging/production |
| is_environment_specific | BOOLEAN | DEFAULT FALSE | 是否环境特定配置 |
| depends_on | JSON |  | 依赖的其他配置 |
| dependents | JSON |  | 被哪些配置依赖 |
| conflicts_with | JSON |  | 冲突的配置 |
| config_group | VARCHAR(50) |  | 配置组名称 |
| group_order | INTEGER | DEFAULT 0 | 组内排序 |
| group_collapsed | BOOLEAN | DEFAULT FALSE | UI中是否默认折叠 |
| hot_reload | BOOLEAN | DEFAULT FALSE | 是否支持热更新 |
| requires_restart | BOOLEAN | DEFAULT TRUE | 是否需要重启生效 |
| restart_services | JSON |  | 需要重启的服务列表 |
| change_notification | JSON |  | 变更通知配置 |
| is_template | BOOLEAN | DEFAULT FALSE | 是否为模板配置 |
| template_name | VARCHAR(100) |  | 模板名称 |
| template_category | VARCHAR(50) |  | 模板分类 |
| template_description | TEXT |  | 模板描述 |
| presets | JSON |  | 预设配置列表 |
| usage_stats | JSON |  | 使用统计 |
| performance_metrics | JSON |  | 性能指标 |
| user_id | INTEGER | FK → users | 用户特定配置 |
| scope | VARCHAR(20) | DEFAULT 'global' | 配置范围：global/user |
| is_inherited | BOOLEAN | DEFAULT TRUE | 是否继承全局配置 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(key)`
- `UNIQUE(scope, user_id, key)`
- `INDEX(category, subcategory)`
- `INDEX(user_id)`
- `INDEX(scope)`

---

#### 4.4.2 scheduled_tasks（调度任务模板）
**用途**：存储系统中所有定时任务的调度配置和处理器定义

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| task_name | VARCHAR(255) | UNIQUE, NOT NULL | 任务名称，全局唯一标识 |
| task_type | VARCHAR(50) | NOT NULL | 任务类型：pt_sync/subscription_check/ai_recommendation/notification_send/scan_media/cleanup等 |
| enabled | BOOLEAN | DEFAULT TRUE | 是否启用该任务 |
| schedule_type | VARCHAR(50) | NOT NULL | 调度类型：cron/interval/one_time/manual |
| schedule_config | JSON |  | 调度配置，JSON格式，根据schedule_type不同而不同 |
| handler | VARCHAR(255) | NOT NULL | 处理器标识，对应后端处理函数路径 |
| handler_params | JSON |  | 处理器参数模板，JSON格式 |
| priority | INTEGER | DEFAULT 0 | 任务优先级，数值越大优先级越高 |
| next_run_at | TIMESTAMP |  | 下次计划执行时间 |
| last_run_at | TIMESTAMP |  | 最后执行时间 |
| last_run_status | VARCHAR(20) |  | 最后执行状态：success/failed/running |
| last_run_duration | INTEGER |  | 最后执行耗时，秒 |
| total_runs | INTEGER | DEFAULT 0 | 总执行次数 |
| success_runs | INTEGER | DEFAULT 0 | 成功执行次数 |
| failed_runs | INTEGER | DEFAULT 0 | 失败执行次数 |
| description | TEXT |  | 任务描述说明 |
| timeout | INTEGER |  | 任务超时时间，秒 |
| max_retries | INTEGER | DEFAULT 3 | 最大重试次数 |
| retry_delay | INTEGER | DEFAULT 60 | 重试延迟，秒 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(task_name)`
- `INDEX(enabled, next_run_at)`
- `INDEX(task_type, enabled)`
- `INDEX(schedule_type)`
- `INDEX(last_run_at DESC)`

**字段说明**：
- **schedule_type 调度类型**：
  - `cron`：使用cron表达式，schedule_config 示例：`{"cron": "0 */6 * * *", "timezone": "Asia/Shanghai"}`
  - `interval`：固定间隔执行，schedule_config 示例：`{"interval": 3600, "unit": "seconds"}`
  - `one_time`：一次性任务，schedule_config 示例：`{"run_at": "2024-01-01T00:00:00Z"}`
  - `manual`：手动触发，不自动执行

- **handler 处理器标识**：
  - 格式：`module.function` 或 `class.method`
  - 示例：`tasks.pt_sync.sync_all_sites`、`tasks.subscription.check_subscriptions`

- **handler_params 参数模板**：
  - 定义任务执行时的默认参数
  - 示例：`{"site_ids": [1, 2, 3], "sync_type": "incremental"}`
  - 实例执行时可被 task_queue.handler_params 覆盖

---

#### 4.4.3 task_queue（任务队列）
**用途**：存储待执行和执行中的任务实例，支持重试和优先级调度

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| scheduled_task_id | INTEGER | FK → scheduled_tasks | 来源的调度任务ID，手动任务可为NULL |
| task_type | VARCHAR(50) | NOT NULL | 任务类型：与scheduled_tasks.task_type一致 |
| task_name | VARCHAR(255) | NOT NULL | 任务名称，可重复（同一任务多次执行） |
| related_type | VARCHAR(50) |  | 关联实体类型：pt_site/subscription/user等 |
| related_id | INTEGER |  | 关联实体ID，如site_id、subscription_id等 |
| status | VARCHAR(20) | DEFAULT 'pending' | 任务状态：pending/running/completed/failed/cancelled/timeout |
| priority | INTEGER | DEFAULT 0 | 任务优先级，数值越大优先级越高 |
| handler | VARCHAR(255) | NOT NULL | 处理器标识，对应后端处理函数路径 |
| handler_params | JSON |  | 处理器参数，JSON格式，优先级高于模板参数 |
| scheduled_at | TIMESTAMP |  | 计划执行时间 |
| started_at | TIMESTAMP |  | 实际开始执行时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 执行耗时，秒 |
| retry_count | INTEGER | DEFAULT 0 | 当前重试次数 |
| max_retries | INTEGER | DEFAULT 3 | 最大重试次数 |
| next_retry_at | TIMESTAMP |  | 下次重试时间 |
| worker_id | VARCHAR(100) |  | 执行该任务的工作进程ID |
| result | JSON |  | 执行结果，JSON格式 |
| error_message | TEXT |  | 错误信息 |
| error_detail | JSON |  | 详细错误信息，JSON格式 |
| progress | INTEGER | CHECK (progress BETWEEN 0 AND 100) | 任务进度 0-100 |
| progress_detail | JSON |  | 进度详情，JSON格式 |
| logs | TEXT |  | 任务执行日志 |
| metadata | JSON |  | 任务元数据，JSON格式 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `INDEX(status, priority DESC, scheduled_at)`
- `INDEX(task_type, status)`
- `INDEX(scheduled_task_id, created_at DESC)`
- `INDEX(related_type, related_id)`
- `INDEX(status, next_retry_at)`
- `INDEX(created_at DESC)`
- `INDEX(worker_id, status)`

**字段说明**：
- **status 任务状态**：
  - `pending`：等待执行
  - `running`：执行中
  - `completed`：执行成功
  - `failed`：执行失败（已达最大重试次数）
  - `cancelled`：已取消
  - `timeout`：执行超时

- **handler_params 参数优先级**：
  - 实例参数（task_queue.handler_params）优先级高于模板参数（scheduled_tasks.handler_params）
  - 执行时合并两者，实例参数覆盖同名模板参数
  - 示例场景：模板定义 `{"sync_type": "incremental"}`，实例覆盖为 `{"sync_type": "full", "force": true}`

- **related_type 和 related_id**：
  - 用于关联业务实体，便于查询某个实体相关的所有任务
  - 示例：`related_type="pt_site", related_id=1` 表示该任务关联 pt_sites 表 id=1 的站点
  - 示例：`related_type="subscription", related_id=5` 表示该任务关联 subscriptions 表 id=5 的订阅

- **重试逻辑**：
  - 任务失败后，如果 `retry_count < max_retries`，自动创建重试
  - `next_retry_at` 根据重试策略计算（指数退避或固定延迟）
  - 达到最大重试次数后，状态变更为 `failed`

---

### 4.5 日志系统表

#### 3.5.1 sync_logs（同步日志）
**用途**：记录PT站点同步任务的详细日志

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| site_id | INTEGER | FK → pt_sites | 站点ID |
| sync_type | VARCHAR(20) | NOT NULL | 同步类型：full/incremental/manual |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 耗时，秒 |
| status | VARCHAR(20) | NOT NULL | 状态：running/success/failed/cancelled |
| total_pages | INTEGER |  | 总翻页数 |
| resources_found | INTEGER |  | 发现资源数 |
| resources_new | INTEGER |  | 新增资源数 |
| resources_updated | INTEGER |  | 更新资源数 |
| resources_skipped | INTEGER |  | 跳过资源数 |
| resources_error | INTEGER |  | 错误资源数 |
| sync_strategy | VARCHAR(20) |  | 同步策略：时间/页码/ID基准 |
| sync_params | JSON |  | 同步参数，JSON |
| error_message | TEXT |  | 错误信息 |
| error_detail | JSON |  | 详细错误，JSON |
| error_resources | JSON |  | 错误资源列表，JSON |
| requests_count | INTEGER |  | 请求次数 |
| avg_response_time | INTEGER |  | 平均响应时间，毫秒 |
| rate_limited | BOOLEAN |  | 是否触发限流 |
| peak_memory_usage | BIGINT |  | 峰值内存使用(字节) |
| cpu_usage_percent | DECIMAL(5,2) |  | CPU使用率 |
| network_bytes_received | BIGINT |  | 网络接收字节数 |
| duplicate_resources | INTEGER | DEFAULT 0 | 重复资源数 |
| invalid_resources | INTEGER | DEFAULT 0 | 无效资源数 |
| quality_distribution | JSON |  | 质量分布统计 |
| incremental_checkpoint | TEXT |  | 增量同步检查点 |
| pages_processed | INTEGER | DEFAULT 0 | 已处理页数 |
| items_per_page | INTEGER | DEFAULT 0 | 每页平均项目数 |
| response_times | JSON |  | 响应时间分布 |
| error_types | JSON |  | 错误类型统计 |
| auto_download_triggered | INTEGER | DEFAULT 0 | 触发的自动下载数 |
| recommendations_generated | INTEGER | DEFAULT 0 | 生成的推荐数 |
| debug_info | JSON |  | 调试信息 |
| sync_version | VARCHAR(20) |  | 同步引擎版本 |
| user_agent | TEXT |  | 使用的User-Agent |
| proxy_used | BOOLEAN | DEFAULT FALSE | 是否使用代理 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(site_id, started_at DESC)`
- `INDEX(status, started_at DESC)`

---

#### 3.5.2 organize_logs（整理日志）
**用途**：记录媒体整理任务的详细日志

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| media_file_id | INTEGER | FK → media_files | 媒体文件ID |
| task_type | VARCHAR(20) | NOT NULL | 任务类型：identify/organize/scrape/all |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 耗时，秒 |
| status | VARCHAR(20) | NOT NULL | 状态：success/failed/cancelled |
| steps | JSON |  | 步骤记录，JSON数组 |
| error_step | VARCHAR(50) |  | 失败步骤 |
| error_message | TEXT |  | 错误信息 |
| error_detail | JSON |  | 详细错误，JSON |
| trigger_type | VARCHAR(20) |  | 触发类型：auto/manual/batch |
| triggered_by | VARCHAR(100) |  | 触发者，如download_complete |
| file_analysis | JSON |  | 文件分析结果 |
| identification_details | JSON |  | 识别详细信息 |
| organization_decision | JSON |  | 整理决策逻辑 |
| scraping_details | JSON |  | 刮削详细信息 |
| media_server_sync | JSON |  | 媒体服务器同步信息 |
| io_operations | JSON |  | IO操作统计 |
| batch_id | VARCHAR(50) |  | 批量操作ID |
| batch_total | INTEGER |  | 批量总数 |
| batch_progress | INTEGER | DEFAULT 0 | 批量进度 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(media_file_id, started_at DESC)`
- `INDEX(status, started_at DESC)`
- `INDEX(task_type, status)`

---

#### 3.5.3 download_logs（下载日志/事件）
**用途**：记录下载任务的关键事件

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| download_task_id | INTEGER | FK → download_tasks | 下载任务ID |
| event_type | VARCHAR(20) | NOT NULL | 事件类型：created/started/paused/resumed/completed/error/deleted |
| message | TEXT |  | 事件描述 |
| data | JSON |  | 事件数据，JSON |
| error_code | VARCHAR(50) |  | 错误代码 |
| error_message | TEXT |  | 错误信息 |
| event_at | TIMESTAMP | NOT NULL | 事件时间 |
| progress_snapshot | JSON |  | 进度快照 |
| network_info | JSON |  | 网络状态信息 |
| seeding_info | JSON |  | 做种信息 |
| file_details | JSON |  | 文件详细信息 |
| client_info | JSON |  | 下载器客户端信息 |
| user_action | VARCHAR(50) |  | 用户操作类型 |
| user_trigger | JSON |  | 用户触发信息 |
| auto_action | JSON |  | 自动化操作记录 |
| alert_info | JSON |  | 告警信息 |
| related_tasks | JSON |  | 相关任务信息 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(download_task_id, event_at DESC)`
- `INDEX(event_type, event_at DESC)`

---

#### 3.5.4 scan_tasks（扫描任务记录）
**用途**：记录目录扫描任务历史

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| scan_type | VARCHAR(20) | NOT NULL | 扫描类型：manual/scheduled/download_complete |
| scan_path | TEXT | NOT NULL | 扫描路径 |
| status | VARCHAR(20) | NOT NULL | 状态：running/completed/failed/cancelled |
| progress | INTEGER | CHECK (0-100) | 进度 0-100 |
| total_files | INTEGER |  | 总文件数 |
| new_files | INTEGER |  | 新增文件数 |
| updated_files | INTEGER |  | 更新文件数 |
| deleted_files | INTEGER |  | 删除文件数 |
| error_files | INTEGER |  | 错误文件数 |
| started_at | TIMESTAMP | NOT NULL | 开始时间 |
| completed_at | TIMESTAMP |  | 完成时间 |
| duration | INTEGER |  | 耗时，秒 |
| error_message | TEXT |  | 错误信息 |
| error_files_detail | JSON |  | 错误文件列表，JSON |
| scan_config | JSON |  | 扫描配置 |
| performance_metrics | JSON |  | 性能指标 |
| user_id | INTEGER | FK → users | 触发用户 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(status, started_at DESC)`
- `INDEX(scan_path)`
- `INDEX(scan_type)`
- `INDEX(user_id)`

---

#### 3.5.5 notification_logs（通知日志）
**用途**：记录所有发送的通知

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| channel_id | INTEGER | FK → notification_channels | 通知渠道ID |
| event_type | VARCHAR(50) | NOT NULL | 事件类型 |
| title | VARCHAR(500) | NOT NULL | 通知标题 |
| message | TEXT | NOT NULL | 通知内容 |
| data | JSON |  | 关联数据，JSON |
| status | VARCHAR(20) | NOT NULL | 状态：pending/sent/failed |
| sent_at | TIMESTAMP |  | 发送时间 |
| error_message | TEXT |  | 错误信息 |
| retry_count | INTEGER | DEFAULT 0 | 重试次数 |
| severity | VARCHAR(20) | DEFAULT 'info' | 严重级别：info/success/warning/error/critical |
| priority | INTEGER | DEFAULT 5 | 消息优先级 |
| delivery_details | JSON |  | 发送详情 |
| read_at | TIMESTAMP |  | 阅读时间 |
| clicked_at | TIMESTAMP |  | 点击时间 |
| action_taken | VARCHAR(50) |  | 用户操作 |
| message_format | VARCHAR(20) | DEFAULT 'text' | 消息格式：text/html/markdown |
| rendered_content | TEXT |  | 渲染后的内容 |
| user_id | INTEGER | FK → users | 目标用户ID |
| session_id | VARCHAR(100) |  | 会话ID |
| test_group | VARCHAR(50) |  | 测试组 |
| template_version | VARCHAR(20) |  | 使用的模板版本 |
| variant | VARCHAR(20) |  | 消息变体 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**：
- `INDEX(channel_id, created_at DESC)`
- `INDEX(status, created_at)`
- `INDEX(user_id, created_at DESC)`
- `INDEX(event_type, severity)`

---

#### 3.5.6 ai_recommendation_logs（AI推荐日志）
**用途**：记录AI推荐的历史和成本

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| recommendation_type | VARCHAR(20) | NOT NULL | 推荐类型：daily/manual/triggered |
| user_profile | JSON |  | 用户画像摘要 |
| available_resources_count | INTEGER |  | 可选资源数量 |
| prompt_tokens | INTEGER |  | Prompt token数 |
| recommendations | JSON |  | 推荐结果，JSON数组 |
| recommendations_count | INTEGER |  | 推荐数量 |
| completion_tokens | INTEGER |  | 返回token数 |
| ai_provider | VARCHAR(20) |  | AI提供商：openai/claude/ollama |
| model_used | VARCHAR(50) |  | 使用的模型名称 |
| estimated_cost | DECIMAL(10,6) |  | 估算成本，USD |
| status | VARCHAR(20) | NOT NULL | 状态：success/failed |
| error_message | TEXT |  | 错误信息 |
| execution_time | INTEGER |  | 执行时长，秒 |
| user_id | INTEGER | FK → users | 用户ID |
| feedback_score | INTEGER | CHECK (1-10) | 用户反馈评分 |
| feedback_received_at | TIMESTAMP |  | 反馈接收时间 |
| click_through_rate | DECIMAL(5,4) |  | 点击率 |
| conversion_count | INTEGER |  | 转化数（下载等） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP |  | 完成时间 |

**索引设计**：
- `INDEX(recommendation_type, created_at DESC)`
- `INDEX(ai_provider, created_at DESC)`
- `INDEX(status)`
- `INDEX(user_id, created_at DESC)`
- `INDEX(model_used, created_at DESC)`

---

## 5. 索引设计策略

### 5.1 主要索引类别

#### 5.1.1 唯一索引（UNIQUE INDEX）
- 确保数据唯一性
- 支持快速查找
- 防止重复数据

#### 5.1.2 复合索引（COMPOSITE INDEX）
- 支持多字段查询
- 优化常用查询模式
- 减少回表操作

#### 5.1.3 条件索引（PARTIAL INDEX）
- 针对特定条件的数据
- 减少索引大小
- 提高查询效率

#### 5.1.4 JSON索引（GIN INDEX）
- 支持JSON字段查询
- 全文搜索支持
- 复杂数据结构查询

### 5.2 查询优化策略

#### 5.2.1 常用查询模式
1. **按时间范围查询**：`INDEX(field, created_at DESC)`
2. **按状态过滤**：`INDEX(status, priority DESC)`
3. **按用户查询**：`INDEX(user_id, created_at DESC)`
4. **全文搜索**：`FULLTEXT INDEX` on text fields

#### 4.2.2 分页查询优化
- 使用覆盖索引避免回表
- 合理的索引顺序支持分页
- 避免大偏移量查询

#### 4.2.3 统计查询优化
- 预计算统计字段
- 使用物化视图
- 合理的聚合索引

### 4.3 性能监控指标

#### 4.3.1 索引使用率
- 查询执行计划分析
- 索引命中率监控
- 慢查询日志分析

#### 4.3.2 存储空间优化
- 定期索引维护
- 统计信息更新
- 索引碎片整理

---

## 6. 数据关系和约束

### 5.1 外键关系图

```
users (1) → (∞) user_profiles
users (1) → (∞) notification_channels
users (1) → (∞) subscriptions

pt_sites (1) → (∞) pt_resources
pt_resources (1) → (1) resource_mappings
unified_resources (1) → (∞) resource_mappings
unified_resources (1) → (∞) download_tasks
download_tasks (1) → (∞) media_files
subscriptions (1) → (∞) subscription_check_logs

notification_channels (1) → (∞) notification_logs

scheduled_tasks (1) → (∞) task_queue
```

### 5.2 业务规则约束

#### 5.2.1 数据完整性
- 每个PT资源只能关联一个统一资源
- 每个统一资源可以有多个推荐资源，但只能有一个主推荐
- 订阅状态转换必须遵循业务规则
- 下载任务状态机管理

#### 5.2.2 数据一致性
- 级联删除策略
- 触发器维护统计字段
- 事务保证数据一致性

#### 5.2.3 业务逻辑约束
- 用户评分范围限制
- 文件大小合理性检查
- 时间戳逻辑验证

---

## 7. 部署和配置建议

### 6.1 数据库选择

#### 6.1.1 SQLite模式
- **适用场景**：个人使用、小规模部署
- **优势**：零配置、轻量级、便携
- **限制**：并发写入限制、功能相对简单

#### 6.1.2 PostgreSQL模式
- **适用场景**：生产环境、高并发需求
- **优势**：功能强大、高性能、丰富的数据类型
- **要求**：独立部署、配置优化

### 6.2 初始化脚本

#### 6.2.1 表结构创建
- 按依赖顺序创建表
- 设置合理的默认值
- 添加必要的约束

#### 6.2.2 基础数据初始化
- 默认管理员用户
- 系统配置默认值
- 常用站点类型配置

### 6.3 性能调优建议

#### 6.3.1 连接池配置
- 合理的连接池大小
- 连接超时设置
- 连接复用策略

#### 6.3.2 查询优化
- 避免N+1查询问题
- 使用合适的JOIN类型
- 合理使用子查询

#### 6.3.3 缓存策略
- 查询结果缓存
- 元数据缓存
- 会话缓存

---

## 8. 扩展性考虑

### 7.1 水平扩展策略

#### 7.1.1 数据分片
- 按用户ID分片
- 按时间分片
- 按地理位置分片

#### 7.1.2 读写分离
- 主从复制配置
- 读写路由策略
- 数据同步延迟控制

### 7.2 分区设计

#### 7.2.1 时间分区
- 按月/年分区日志表
- 自动分区管理
- 历史数据归档

#### 7.2.2 功能分区
- 按业务模块分区
- 冷热数据分离
- 查询性能优化

### 7.3 缓存策略

#### 7.3.1 多级缓存
- 应用层缓存
- 数据库缓存
- CDN缓存

#### 7.3.2 缓存更新策略
- 主动更新
- 被动失效
- 定时刷新

### 7.4 监控和维护

#### 7.4.1 性能监控
- 查询性能监控
- 数据库资源监控
- 应用性能监控

#### 7.4.2 自动化维护
- 定期数据清理
- 索引维护
- 统计信息更新

---

## 总结

本数据库设计文档详细描述了PT站点媒体资源管理系统的完整数据架构，涵盖了21个核心表的设计，支持：

1. **完整的业务流程**：从PT站点同步到媒体库入库的完整链路
2. **统一任务调度**：基于模板-实例模式的任务调度和队列管理系统
3. **灵活的扩展能力**：JSON字段支持复杂配置和业务扩展
4. **高性能查询**：合理的索引设计支持快速检索
5. **完整的日志记录**：支持问题排查和性能分析
6. **用户友好体验**：个性化配置和智能推荐功能

该设计既考虑了当前的功能需求，也为未来的扩展和优化预留了空间，是一个完整、专业、可扩展的数据库架构方案。