# 项目介绍

**NasFusion** 是一个基于 PT（Private Tracker）站点的媒体资源管理系统，专为 NAS 用户设计。

## 核心理念

传统媒体管理工具（如 Radarr/Sonarr）以 TMDB 为起点搜索资源，NasFusion 反其道而行之：

> **PT 优先** — 以 PT 站点已有资源为起点，先发现资源，再关联元数据。

这带来以下优势：
- 站点资源本地缓存，搜索速度极快
- 无需频繁访问 PT 站点，降低封号风险
- 精准匹配促销资源，最大化下载价值

## 功能全览

| 模块 | 功能 |
|------|------|
| PT 站点管理 | 多站点配置、健康检查、代理支持 |
| 资源同步 | 定时同步、去重、促销识别、季集识别 |
| 资源识别 | 自动识别类型、TMDB/豆瓣元数据关联 |
| 订阅系统 | 电视剧季度订阅、质量优先级、自动下载 |
| 媒体文件管理 | 文件扫描、整理规则、目录管理 |
| 下载管理 | qBittorrent 集成、任务监控 |
| 媒体服务器 | Jellyfin/Emby/Plex 集成、观看历史同步 |
| 通知系统 | Telegram/Email、事件驱动推送 |
| 任务调度 | 后台任务、进度跟踪、历史记录 |

## 技术栈

- **后端**：FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL/SQLite
- **前端**：Vue 3 + TypeScript + Element Plus
- **任务调度**：APScheduler + asyncio
- **AI 集成**：OpenAI API（智能推荐）

## 下一步

- [快速开始 →](./quick-start)
- [Docker 部署 →](../deploy/docker)
