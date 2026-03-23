# NasFusion AI Agent Skills

Skills 是高级工作流，编排多个单步 Tool 完成复合场景，减少 LLM 多轮调用。

## 目录结构

```
skills/
├── SKILLS.md             # 本文件：全部 Skill 的功能说明（人类查阅）
├── base.py               # BaseSkill 基类（继承 BaseTool）
├── subscribe_tv.py       # 追剧订阅
├── subscribe_movie.py    # 电影订阅
├── smart_download.py     # 智能下载
├── dashboard.py          # 系统总览
├── trending_download.py  # 榜单下载
└── __init__.py           # 导出全部 Skill，触发 @register_tool 注册
```

## 新增 Skill 规范

1. 创建 `skills/{name}.py`，继承 `BaseSkill`，加 `@register_tool`
2. 类属性写明 `name`、`description`、`parameters`（与 Tool 一致）
3. 实现 `execute()` 方法，内部调用已有 Tool 编排流程
4. 在 `__init__.py` 导出新类
5. 在本文件追加说明

---

## 已有 Skills

### 1. `subscribe_tv` — 追剧订阅

**文件**：`subscribe_tv.py`
**典型用法**：「帮我追《黑镜》第7季」「订阅最新一季的《纸牌屋》」

**编排步骤**：
1. `resource_search`：确认 PT 站点存在该剧资源
2. `subscription_create`（media_type=tv）：在媒体库中查找并创建订阅

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 剧集名称 |
| season | integer | ✅ | 订阅季数 |
| quality_mode | string | - | first_match / best_match（默认 best_match） |

**前置条件**：剧集须已在本地媒体库中识别过

---

### 2. `subscribe_movie` — 电影订阅

**文件**：`subscribe_movie.py`
**典型用法**：「订阅《复仇者联盟5》」「帮我自动下载《哪吒3》上映后的资源」

**编排步骤**：
1. `resource_search`：确认 PT 站点存在该电影资源
2. `subscription_create`（media_type=movie）：在媒体库中查找并创建订阅

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 电影名称 |
| tmdb_id | integer | - | TMDB ID，精确匹配时使用 |
| quality_mode | string | - | first_match / best_match（默认 best_match） |

**前置条件**：电影须已在本地媒体库中识别过

---

### 3. `smart_download` — 智能下载

**文件**：`smart_download.py`
**典型用法**：「下载《流浪地球2》1080p」「帮我下载最新的阿凡达，要免费的」

**编排步骤**：
1. `resource_search`：按标题搜索候选资源（prefer_free=true 时先搜免费，无结果再放开）
2. 内部选优：免费资源优先 → 做种数最多
3. `download_create`：创建下载任务

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 影视名称 |
| media_type | string | - | movie / tv |
| resolution | string | - | 2160p / 1080p / 720p / 480p |
| prefer_free | boolean | - | 是否优先免费资源（默认 true） |

---

### 4. `dashboard` — 系统总览

**文件**：`dashboard.py`
**典型用法**：「系统现在怎么样」「给我看看总体情况」「有什么在下载吗」

**编排步骤**（按 focus 参数选择性执行）：
1. `system_status`：站点、下载器、资源总数状态
2. `download_status`：当前下载任务概况（最近 10 条）
3. `subscription_list`：活跃订阅列表

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| focus | string | - | downloads / subscriptions / system / all（默认 all） |

---

### 5. `trending_download` — 榜单下载

**文件**：`trending_download.py`
**典型用法**：「下载豆瓣热门电影第一名」「把 TMDB 评分最高的电影下载下来」

**编排步骤**：
1. `trending_query`：查询指定榜单
2. 取指定名次的影片标题
3. `resource_search`：搜索 PT 资源（prefer_free 时先搜免费）
4. 内部选优：免费优先 → 做种数最多
5. `download_create`：创建下载任务

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| collection_type | string | - | 榜单类型（默认 douban_hot_movie） |
| rank | integer | - | 榜单名次（默认第 1 名） |
| resolution | string | - | 期望分辨率（不限则不填） |
| prefer_free | boolean | - | 是否优先免费资源（默认 true） |

**支持的榜单**：
- `douban_hot_movie`：豆瓣热门电影
- `douban_top250_movie`：豆瓣 Top250 电影
- `douban_hot_tv`：豆瓣热门剧集
- `tmdb_popular_movie`：TMDB 热门电影
- `tmdb_top_rated_movie`：TMDB 评分最高电影
- `tmdb_popular_tv`：TMDB 热门剧集
