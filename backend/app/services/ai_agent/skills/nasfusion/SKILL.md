---
name: nasfusion
description: NasFusion 媒体资源管理技能集。当用户需要订阅追剧/电影、下载影视资源、查看系统状态、从榜单下载时调用。包含 subscribe_tv、subscribe_movie、smart_download、dashboard、trending_download 五个技能。
---

# NasFusion Skills

当用户意图明确匹配以下场景时，优先调用对应 Skill，而非拆成多步单工具调用。

## subscribe_tv — 追剧订阅
**触发词**：追剧、追番、订阅剧集、以后自动下载新集
**示例**：「帮我追《黑镜》第7季」「订阅《纸牌屋》最新季」
**必填**：title（剧名）、season（季数）
**可选**：quality_mode（first_match 速度优先 / best_match 质量优先，默认 best_match）
**前提**：剧集须已在媒体库中识别过

---

## subscribe_movie — 电影订阅
**触发词**：订阅电影、上映后自动下载、出资源了帮我下
**示例**：「订阅《复仇者联盟5》」「《哪吒3》出资源后帮我自动下载」
**必填**：title（电影名）
**可选**：tmdb_id（精确匹配用）、quality_mode
**前提**：电影须已在媒体库中识别过

---

## smart_download — 智能下载
**触发词**：下载、帮我下、找个资源下
**示例**：「下载《流浪地球2》1080p」「帮我下最新的阿凡达」「下载免费版黑镜第6季」
**必填**：title（影视名）
**可选**：media_type（movie/tv）、resolution（2160p/1080p/720p/480p）、prefer_free（默认 true）
**说明**：自动选优，免费资源优先，相同条件下做种数最多者优先

---

## dashboard — 系统总览
**触发词**：系统怎么样、总体情况、在下什么、订阅正常吗
**示例**：「系统现在怎么样」「有什么在下载吗」「我的订阅都正常吗」
**可选**：focus（downloads / subscriptions / system / all，默认 all）

---

## trending_download — 榜单下载
**触发词**：榜单下载、下载排行第一、下载热门、下载豆瓣/TMDB 推荐
**示例**：「下载豆瓣热门电影第一名」「把 TMDB 评分最高电影下载下来」「豆瓣 Top250 第5名下载」
**可选**：collection_type（默认 douban_hot_movie）、rank（默认 1）、resolution、prefer_free
**支持榜单**：douban_hot_movie / douban_top250_movie / douban_hot_tv / tmdb_popular_movie / tmdb_top_rated_movie / tmdb_popular_tv
