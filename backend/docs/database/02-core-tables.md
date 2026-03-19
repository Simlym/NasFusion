# 核心业务表

## 1. pt_sites（PT站点配置）✅ 已实现

**用途**：存储用户配置的所有PT站点信息

**实现状态**：✅ 已完整实现（模型文件：`app/models/pt_site.py`）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | Integer | PK, AUTOINCREMENT | 主键 |
| name | String(100) | NOT NULL | 站点名称（如"MTeam"） |
| type | String(50) | NOT NULL | 站点类型（如"mteam", "chd"，对应爬虫适配器） |
| domain | String(255) | UNIQUE, NOT NULL, INDEX | 站点域名 |
| base_url | String(500) | NOT NULL | 完整URL |
| auth_type | String(50) | NOT NULL | 认证方式（cookie/passkey/user_pass） |
| auth_cookie | Text | NULL | Cookie（加密存储） |
| auth_passkey | String(255) | NULL | Passkey（加密存储） |
| auth_username | String(255) | NULL | 用户名（加密存储） |
| auth_password | String(255) | NULL | 密码（加密存储） |
| cookie_expire_at | DateTime | NULL | Cookie过期时间 |
| proxy_config | JSON | NULL | 代理配置 |
| capabilities | JSON | NULL | 站点能力配置 |
| sync_enabled | Boolean | NOT NULL, DEFAULT TRUE | 是否启用同步 |
| sync_strategy | String(50) | NULL | 同步策略（time_based/page_based/id_based） |
| sync_interval | Integer | NULL | 同步间隔（分钟） |
| sync_config | JSON | NULL | 同步详细配置 |
| last_sync_at | DateTime | NULL | 最后同步时间 |
| last_sync_status | String(50) | NULL | 最后同步状态（success/failed/running） |
| last_sync_error | Text | NULL | 最后同步错误信息 |
| request_interval | Integer | NULL | 请求间隔（秒） |
| max_requests_per_day | Integer | NULL | 每日最大请求数 |
| daily_requests_used | Integer | NOT NULL, DEFAULT 0 | 今日已用请求数 |
| status | String(50) | NOT NULL, DEFAULT 'active' | 站点状态（active/inactive/error） |
| health_check_at | DateTime | NULL | 最后健康检查时间 |
| health_status | String(50) | NULL | 健康状态（healthy/unhealthy） |
| total_resources | Integer | NOT NULL, DEFAULT 0 | 总资源数 |
| total_synced | Integer | NOT NULL, DEFAULT 0 | 已同步数 |
| created_at | DateTime | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(domain)`
- `INDEX(domain)` - 单独索引（已在字段定义中实现）

---

## 2. pt_resources（PT原始资源）✅ 已实现

**用途**：存储从PT站点爬取的原始种子信息

**实现状态**：✅ 已完整实现（模型文件：`app/models/pt_resource.py`）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| site_id | INTEGER | FK → pt_sites, NOT NULL, INDEX | 站点ID |
| torrent_id | VARCHAR(200) | NOT NULL | 站点内种子ID |
| title | VARCHAR(1000) | NOT NULL | 原始标题 |
| subtitle | VARCHAR(500) | NULL | 副标题 |
| category | VARCHAR(20) | NULL, INDEX | 分类：movie/tv/music/book/other |
| size_bytes | BIGINT | NOT NULL | 文件大小，字节 |
| file_count | INTEGER | NOT NULL, DEFAULT 1 | 文件数量 |
| torrent_hash | VARCHAR(40) | NULL | 种子哈希，InfoHash |
| seeders | INTEGER | NOT NULL, DEFAULT 0 | 做种数 |
| leechers | INTEGER | NOT NULL, DEFAULT 0 | 下载数 |
| completions | INTEGER | NOT NULL, DEFAULT 0 | 完成数 |
| last_seeder_update_at | TIMESTAMP | NULL | 做种数最后更新时间 |
| promotion_type | VARCHAR(20) | NULL | 促销类型：free/50%/2x/2x50%/none |
| promotion_expire_at | TIMESTAMP | NULL | 促销结束时间 |
| is_free | BOOLEAN | NOT NULL, DEFAULT FALSE, INDEX | 快速查询是否免费 |
| is_discount | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否折扣 |
| is_double_upload | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否双倍上传 |
| has_hr | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否有HR要求 |
| hr_days | INTEGER | NULL | 需要保种天数 |
| hr_seed_time | INTEGER | NULL | 需要保种小时数 |
| hr_ratio | DECIMAL(5,2) | NULL | 需要分享率 |
| resolution | VARCHAR(20) | NULL | 分辨率：2160p/1080p/720p等 |
| source | VARCHAR(50) | NULL | 来源：BluRay/WEB-DL/HDTV等 |
| codec | VARCHAR(50) | NULL | 编码：x264/x265/AV1等 |
| audio | JSON | NULL | 音轨信息，JSON数组 |
| subtitle_info | JSON | NULL | 字幕信息，JSON数组 |
| quality_tags | JSON | NULL | 其他质量标签，JSON数组 |
| imdb_id | VARCHAR(20) | NULL, INDEX | IMDB ID |
| imdb_rating | DECIMAL(3,1) | NULL | IMDB评分 |
| douban_id | VARCHAR(20) | NULL, INDEX | 豆瓣ID |
| douban_rating | DECIMAL(3,1) | NULL | 豆瓣评分 |
| tmdb_id | INTEGER | NULL | TMDB ID |
| description | TEXT | NULL | 完整描述（BB代码） |
| mediainfo | TEXT | NULL | MediaInfo信息 |
| origin_file_name | VARCHAR(500) | NULL | 原始种子文件名 |
| image_list | JSON | NULL | 图片列表，JSON数组 |
| detail_fetched | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否已获取详情 |
| detail_fetched_at | TIMESTAMP | NULL | 详情获取时间 |
| douban_info | JSON | NULL | 豆瓣详细信息，JSON |
| douban_fetched | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否已获取豆瓣信息 |
| douban_fetched_at | TIMESTAMP | NULL | 豆瓣信息获取时间 |
| detail_url | TEXT | NULL | 详情页URL |
| download_url | TEXT | NOT NULL | 下载链接 |
| magnet_link | TEXT | NULL | 磁力链接 |
| raw_page_html | TEXT | NULL | 原始页面HTML内容（用于调试和问题排查） |
| raw_page_json | JSON | NULL | 原始页面解析后的结构化数据 |
| raw_detail_json | JSON | NULL | 详情接口原始数据，JSON |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE, INDEX | 是否有效 |
| last_check_at | TIMESTAMP | NULL | 最后检查时间 |
| published_at | TIMESTAMP | NULL, INDEX | 发布时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 入库时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(site_id, torrent_id)`
- `INDEX(site_id)` - 单独索引（已在字段定义中实现）
- `INDEX(category)` - 单独索引（已在字段定义中实现）
- `INDEX(imdb_id)` - 单独索引（已在字段定义中实现）
- `INDEX(douban_id)` - 单独索引（已在字段定义中实现）
- `INDEX(is_free)` - 单独索引（已在字段定义中实现）
- `INDEX(is_active)` - 单独索引（已在字段定义中实现）
- `INDEX(published_at)` - 单独索引（已在字段定义中实现）

**字段说明**：
- **raw_page_html**：保存完整的原始HTML页面，用于调试解析问题和数据验证
- **raw_page_json**：保存解析后的结构化数据，便于查询和分析原始信息
- **raw_detail_json**：保存详情接口返回的原始JSON数据
- **description**：从详情页获取的完整描述（BB代码格式）
- **mediainfo**：从详情页获取的MediaInfo信息
- **image_list**：资源相关的图片列表
- **detail_fetched** / **douban_fetched**：标记是否已获取详细信息，避免重复请求
- 这些字段为可选字段，建议根据存储策略选择性保存重要或异常的记录

---

## 3. 统一媒体资源表（按类型拆分）

**设计理念**：为优化查询性能和存储效率，将统一资源表按媒体类型拆分为6个专用表。每个表只包含该类型媒体相关的字段，避免大量NULL值，提升查询效率。

### 3.1 unified_movies（电影资源表）✅ 已实现

**用途**：存储电影媒体的统一元数据

**实现状态**：✅ 已完整实现（模型文件：`app/models/unified_movie.py`）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| tmdb_id | INTEGER | UNIQUE, INDEX | TMDB ID |
| imdb_id | VARCHAR(20) | UNIQUE, INDEX | IMDB ID |
| douban_id | VARCHAR(20) | UNIQUE, INDEX | 豆瓣ID |
| title | VARCHAR(500) | NOT NULL | 主标题（通常为中文） |
| original_title | VARCHAR(500) | NULL | 原始语言标题 |
| aka | JSON | NULL | 别名/译名，JSON数组 |
| year | INTEGER | NULL, INDEX | 年份 |
| release_date | DATE | NULL, INDEX | 上映日期 |
| runtime | INTEGER | NULL | 时长（分钟） |
| rating_tmdb | DECIMAL(3,1) | NULL | TMDB评分 |
| rating_douban | DECIMAL(3,1) | NULL | 豆瓣评分 |
| rating_imdb | DECIMAL(3,1) | NULL | IMDB评分 |
| votes_count | INTEGER | NULL | 投票数 |
| genres | JSON | NULL | 类型，JSON数组 |
| tags | JSON | NULL | 标签，JSON数组 |
| languages | JSON | NULL | 语言，JSON数组 |
| countries | JSON | NULL | 国家，JSON数组 |
| directors | JSON | NULL | 导演，JSON数组 |
| actors | JSON | NULL | 演员，JSON数组（含角色名、头像） |
| writers | JSON | NULL | 编剧，JSON数组 |
| overview | TEXT | NULL | 简介（优先中文） |
| tagline | VARCHAR(500) | NULL | 宣传语 |
| certification | VARCHAR(20) | NULL | 分级（PG-13, R等） |
| collection_id | INTEGER | NULL | 系列ID |
| collection_name | VARCHAR(200) | NULL | 系列名 |
| budget | BIGINT | NULL | 预算 |
| revenue | BIGINT | NULL | 票房 |
| production_companies | JSON | NULL | 制作公司，JSON数组 |
| status | VARCHAR(20) | NULL | 状态：Released/Post_Production/Rumored |
| poster_url | TEXT | NULL | 海报URL |
| backdrop_url | TEXT | NULL | 背景图URL |
| logo_url | TEXT | NULL | Logo URL |
| clearart_url | TEXT | NULL | 透明艺术图URL |
| banner_url | TEXT | NULL | 横幅URL |
| pt_resource_count | INTEGER | NOT NULL, DEFAULT 0 | 关联的PT资源数量 |
| has_free_resource | BOOLEAN | NOT NULL, DEFAULT FALSE, INDEX | 是否有Free资源 |
| best_quality | VARCHAR(20) | NULL | 最佳质量：4K/1080P等 |
| best_seeder_count | INTEGER | NOT NULL, DEFAULT 0 | 最高做种数 |
| last_resource_updated_at | TIMESTAMP | NULL | PT资源最后更新时间 |
| local_file_count | INTEGER | NOT NULL, DEFAULT 0 | 本地文件数量 |
| has_local | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否有本地文件 |
| local_images_dir | VARCHAR(500) | NULL | 本地图片目录 |
| detail_loaded | BOOLEAN | NOT NULL, DEFAULT FALSE | 详情是否已加载 |
| detail_loaded_at | TIMESTAMP | NULL | 详情加载时间 |
| metadata_source | VARCHAR(20) | NULL | 元数据来源：douban/tmdb |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(tmdb_id)` - 唯一索引（已在字段定义中实现）
- `UNIQUE(imdb_id)` - 唯一索引（已在字段定义中实现）
- `UNIQUE(douban_id)` - 唯一索引（已在字段定义中实现）
- `INDEX(tmdb_id)` - 单独索引（已在字段定义中实现）
- `INDEX(imdb_id)` - 单独索引（已在字段定义中实现）
- `INDEX(douban_id)` - 单独索引（已在字段定义中实现）
- `INDEX(year)` - 单独索引（已在字段定义中实现）
- `INDEX(release_date)` - 单独索引（已在字段定义中实现）
- `INDEX(has_free_resource)` - 单独索引（已在字段定义中实现）

**字段说明**：
- **title** vs **title_zh**：实际实现中使用 `title` 作为主标题（通常为中文），而非 `title_zh`
- **original_title**：原始语言标题（如英文原名）
- **aka**：别名/译名数组，用于存储多个译名和别名
- **tagline**：电影宣传语
- **certification**：分级信息（如 PG-13, R 等）
- **collection_id/collection_name**：电影系列信息（如漫威电影宇宙）
- **poster_url** vs **poster_thumb_url/poster_full_url**：实际实现使用单一 `poster_url`，而非分离的缩略图和完整图
- **clearart_url/banner_url**：额外的图片资源
- **local_images_dir**：本地图片存储目录

---

### 3.2 unified_tv_series（剧集资源表）
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

### 3.3 unified_music（音乐资源表）
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

### 3.4 unified_books（书籍资源表）
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

### 3.5 unified_anime（动画资源表）
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

### 3.6 unified_adult（成人内容资源表）
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

## 4. resource_mappings（资源关联映射）✅ 已实现

**用途**：PT原始资源与统一资源的多对一映射关系

**实现状态**：✅ 已实现（模型文件：`app/models/resource_mapping.py`）

**设计差异说明**：
- 原设计采用通用多态设计（`unified_table_name` + `unified_resource_id`）
- 实际实现采用专用外键设计（`unified_movie_id`、`unified_tv_id` 等），更符合关系型数据库规范
- 使用 `media_type` 字段标识媒体类型，通过 CheckConstraint 确保外键一致性

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| pt_resource_id | INTEGER | FK → pt_resources, UNIQUE, NOT NULL, INDEX | PT资源ID（一个PT资源只能映射到一个统一资源） |
| media_type | VARCHAR(20) | NOT NULL, INDEX | 媒体类型：movie/tv/music/book/anime/adult |
| unified_movie_id | INTEGER | FK → unified_movies, NULL, INDEX | 电影资源ID（仅当media_type='movie'时有值） |
| match_method | VARCHAR(20) | NULL, INDEX | 匹配方式：id_exact/title_year/title_fuzzy/manual |
| match_confidence | INTEGER | NULL, CHECK (0-100) | 匹配置信度 |
| match_score_detail | JSON | NULL | 匹配得分详情，JSON |
| is_primary | BOOLEAN | NOT NULL, DEFAULT FALSE, INDEX | 是否主推荐资源（用于多个PT资源时标记最佳） |
| recommendation_score | INTEGER | NULL, CHECK (0-100) | 推荐度评分 |
| recommendation_reason | JSON | NULL | 推荐理由，JSON |
| is_verified | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否人工确认 |
| verified_by | INTEGER | NULL | 确认者用户ID |
| verified_at | TIMESTAMP | NULL | 确认时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引设计**：
- `UNIQUE(pt_resource_id)` - 唯一索引（已在字段定义中实现）
- `INDEX(pt_resource_id)` - 单独索引（已在字段定义中实现）
- `INDEX(media_type)` - 单独索引（已在字段定义中实现）
- `INDEX(unified_movie_id)` - 单独索引（已在字段定义中实现）
- `INDEX(match_method)` - 单独索引（已在字段定义中实现）
- `INDEX(is_primary)` - 单独索引（已在字段定义中实现）

**约束设计**：
- `CHECK((media_type = 'movie' AND unified_movie_id IS NOT NULL) OR (media_type != 'movie' AND unified_movie_id IS NULL))` - 确保media_type与外键一致
- `CHECK(match_confidence >= 0 AND match_confidence <= 100)` - 匹配置信度范围
- `CHECK(recommendation_score IS NULL OR (recommendation_score >= 0 AND recommendation_score <= 100))` - 推荐度评分范围

**待实现字段**（其他媒体类型的外键）：
- `unified_tv_id` - 电视剧资源ID
- `unified_music_id` - 音乐资源ID
- `unified_book_id` - 书籍资源ID
- `unified_anime_id` - 动漫资源ID
- `unified_adult_id` - 成人内容资源ID

**字段说明**：
- **专用外键设计**：每种媒体类型使用独立的外键字段，通过 CheckConstraint 确保一致性
- **pt_resource_id UNIQUE**：一个PT资源只能映射到一个统一资源，确保映射关系明确
- **is_primary**：当一个统一电影有多个PT资源时，标记推荐下载的资源
- **match_method**：记录匹配方式，便于调试和优化匹配算法
- **match_confidence**：匹配置信度，用于展示和排序
- **is_verified**：人工确认的映射关系具有最高优先级

---

## 5. download_tasks（下载任务）
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

---

## 6. media_files（媒体文件）
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
