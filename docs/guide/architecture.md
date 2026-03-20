# 系统架构

本文介绍 NasFusion 的整体技术架构，帮助你了解系统的设计理念和各模块的职责。

## 整体架构图

<!-- 图：系统整体架构图 -->
<!-- ![系统架构](/images/architecture/overview.png) -->

::: tip 图片预留位置
*系统整体架构图：展示前端、后端、数据库、外部服务之间的关系*
:::

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                            │
│              Vue 3 + TypeScript + Element Plus               │
│         (浏览器访问 http://localhost:3000)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                        API 网关层                            │
│                  FastAPI (Port 8000)                         │
│              RESTful API + OpenAPI 文档                      │
└────────┬──────────────────────────────────────┬─────────────┘
         │                                      │
┌────────▼───────────────┐        ┌─────────────▼─────────────┐
│      业务逻辑层         │        │        任务调度层          │
│    Service Layer       │        │      APScheduler           │
│  - PTSiteService       │        │  - 资源同步任务            │
│  - SubscriptionService │        │  - 健康检查任务            │
│  - MediaFileService    │        │  - 下载监控任务            │
│  - DownloadService     │        │  - 媒体库同步任务          │
│  - NotificationService │        └─────────────┬─────────────┘
└────────┬───────────────┘                       │
         │                                       │
┌────────▼───────────────────────────────────────▼─────────────┐
│                        数据访问层                              │
│              SQLAlchemy 2.0 Async ORM                         │
│         SQLite（开发）/ PostgreSQL（生产）                     │
└───────────────────────────────────────────────────────────────┘
         │ 适配器层（Adapters）
         ├─► PT 站点适配器（MTeam / NexusPHP）
         ├─► 下载器适配器（qBittorrent）
         ├─► 媒体服务器适配器（Jellyfin / Emby / Plex）
         ├─► 元数据适配器（TMDB / 豆瓣）
         └─► 通知渠道适配器（Telegram / SMTP）
```

## 核心设计原则

### 1. PT 优先（PT-First）

不同于传统工具以 TMDB 为数据源，NasFusion **以 PT 站点资源为主数据**：

```
传统工具：TMDB → 搜索 PT 站点 → 下载
NasFusion：PT 站点 → 本地缓存 → 搜索/匹配 → 下载
```

本地缓存带来的好处：
- 搜索响应时间 < 100ms（无需实时访问 PT 站点）
- 降低 PT 站点访问频率，减少封号风险
- 可以离线浏览和检索资源

### 2. 适配器模式

所有外部系统通过**适配器**接入，核心业务逻辑与外部系统解耦：

<!-- 图：适配器模式示意图 -->
<!-- ![适配器模式](/images/architecture/adapter-pattern.png) -->

::: tip 图片预留位置
*适配器模式示意图：核心业务层通过统一接口调用不同的外部服务适配器*
:::

```
backend/app/adapters/
├── pt_sites/
│   ├── base.py          # BasePTSiteAdapter（抽象基类）
│   ├── mteam.py         # MTeam 适配器
│   └── nexusphp.py      # NexusPHP 通用适配器
├── downloaders/
│   ├── base.py          # BaseDownloaderAdapter
│   └── qbittorrent.py   # qBittorrent 适配器
├── media_servers/
│   ├── base.py
│   ├── jellyfin.py
│   ├── emby.py
│   └── plex.py
└── metadata/
    ├── tmdb.py
    └── douban.py
```

新增一个 PT 站点只需继承 `BasePTSiteAdapter` 实现对应接口，无需改动核心业务。

### 3. 事件驱动（Event-Driven）

系统采用**发布-订阅**模式解耦业务逻辑和副作用（如通知）：

```
下载完成
    │
    ├──► 发布事件：download_completed
    │
    ├──► 订阅者 A：通知服务 → 推送 Telegram/邮件
    ├──► 订阅者 B：媒体整理服务 → 移动文件
    └──► 订阅者 C：媒体库服务 → 刷新 Jellyfin
```

<!-- 图：事件总线流程图 -->
<!-- ![事件总线](/images/architecture/event-bus.png) -->

::: tip 图片预留位置
*事件总线流程图：展示事件发布后各订阅者的响应链路*
:::

### 4. 任务处理器注册表

后台任务使用**注册表模式**统一管理：

```python
# 每个任务类型有独立的处理器
TaskHandlerRegistry.register(TASK_TYPE_SYNC, SyncTaskHandler)
TaskHandlerRegistry.register(TASK_TYPE_SCRAPE, ScrapeTaskHandler)

# 执行时动态查找处理器
handler = TaskHandlerRegistry.get(task.type)
await handler.execute(db, params, execution_id)
```

## 数据流

### 资源同步流

```
APScheduler 触发
    │
    ▼
SyncTaskHandler.execute()
    │
    ▼
MTeamAdapter.fetch_resources()  ← 访问 PT 站点 API
    │
    ▼
数据清洗 & 解析（季集识别、促销解析）
    │
    ▼
写入 pt_resources 表（upsert 去重）
    │
    ▼
发布事件：resources_synced
    │
    ▼
SubscriptionService 自动匹配订阅
```

### 订阅触发流

```
新资源入库
    │
    ▼
遍历活跃订阅
    │
    ▼
资源匹配（标题 + 集数 + 质量）
    │
    ▼
质量优先级打分
    │
    ▼
选出最优资源
    │
    ▼
调用 qBittorrent 添加下载任务
    │
    ▼
记录下载状态 + 发布事件
    │
    ├──► 通知：已开始下载 S01E01
    └──► 监控：等待下载完成
```

<!-- 图：完整数据流图 -->
<!-- ![数据流](/images/architecture/data-flow.png) -->

::: tip 图片预留位置
*完整数据流图：从资源同步到文件入库的完整数据流向*
:::

## 目录结构

```
backend/
├── app/
│   ├── adapters/          # 外部系统适配器
│   ├── api/v1/            # REST API 路由
│   │   ├── pt_sites.py    # PT 站点管理 API
│   │   ├── resources.py   # 资源搜索 API
│   │   ├── subscriptions.py
│   │   ├── downloads.py
│   │   └── tasks.py
│   ├── constants/         # 常量定义（避免魔法字符串）
│   ├── core/
│   │   ├── config.py      # 全局配置（Pydantic Settings）
│   │   ├── database.py    # 数据库连接管理
│   │   └── dependencies.py # FastAPI 依赖注入
│   ├── events/
│   │   ├── bus.py         # 事件总线核心
│   │   └── handlers/      # 事件处理器
│   ├── models/            # SQLAlchemy ORM 模型
│   ├── schemas/           # Pydantic 请求/响应模型
│   ├── services/          # 业务逻辑层（核心）
│   ├── tasks/
│   │   ├── registry.py    # 任务处理器注册表
│   │   └── handlers/      # 各类型任务处理器
│   └── utils/             # 工具函数
├── alembic/               # 数据库迁移脚本
└── data/                  # 运行时数据（数据库、日志）

frontend/
├── src/
│   ├── api/               # API 调用封装（对应后端路由）
│   ├── components/        # 可复用 Vue 组件
│   ├── views/             # 页面级组件
│   ├── stores/            # Pinia 状态管理
│   └── router/            # Vue Router 配置
```

## 数据库模型关系

```
User
 └── 1:N ──► UserMediaServer（媒体服务器配置）

PTSite
 └── 1:N ──► PTResource（同步的资源）

PTResource
 └── N:1 ──► MediaInfo（关联元数据）
 └── 1:N ──► DownloadTask（下载任务）

Subscription（订阅）
 └── N:1 ──► MediaInfo（订阅的剧集）
 └── 1:N ──► SubscriptionEpisode（每集状态）

DownloadTask
 └── N:1 ──► PTResource
 └── 1:1 ──► MediaFile（整理后的文件）
```

<!-- 图：ER 关系图 -->
<!-- ![ER 图](/images/architecture/er-diagram.png) -->

::: tip 图片预留位置
*数据库 ER 关系图：展示各表之间的关联关系*
:::

## 技术选型说明

| 选择 | 原因 |
|------|------|
| **FastAPI** | 原生异步支持，自动生成 OpenAPI 文档，类型安全 |
| **SQLAlchemy 2.0 Async** | 成熟 ORM，支持异步，与 FastAPI 搭配完善 |
| **APScheduler** | 轻量灵活，支持多种调度策略，无需额外消息队列 |
| **Vue 3 + Element Plus** | 组件丰富，适合管理后台，TypeScript 支持好 |
| **SQLite / PostgreSQL 双支持** | SQLite 降低部署门槛，PostgreSQL 满足生产需求 |
