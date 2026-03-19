# NasFusion 数据库设计文档

> **PT站点媒体资源管理系统** - 完整数据库设计文档

## 📖 文档导航

### 快速开始
- **推荐阅读顺序**：01 → 02 → 04 → 其他
- **查看已实现功能**：标有 ✅ 的章节
- **规划中功能**：标有 🚧 的章节

### 文档索引

| 序号 | 文档 | 说明 | 状态 | 主要内容 |
|------|------|------|------|----------|
| 01 | [系统概述](./01-overview.md) | 项目简介、设计原则、架构总览 | ✅ | 核心理念、技术栈、数据流设计 |
| 02 | [核心业务表](./02-core-tables.md) | PT站点、资源、统一资源、映射 | ✅ 部分实现 | `pt_sites`, `pt_resources`, `unified_movies`, `resource_mappings` |
| 03 | [订阅系统表](./03-subscription-tables.md) | 订阅管理、检查日志 | ✅ 已实现 | `subscriptions`, `subscription_check_logs` |
| 04 | [用户系统表](./04-user-tables.md) | 用户、配置、通知渠道 | ✅ 已实现 | `users`, `user_profiles`, `notification_channels` |
| 05 | [系统管理表](./05-system-tables.md) | 系统配置、任务调度 | 🚧 待实现 | `system_settings`, `scheduled_tasks`, `task_queue` |
| 06 | [日志系统表](./06-log-tables.md) | 同步、下载、扫描、推荐日志 | 🚧 待实现 | `sync_logs`, `download_logs`, `ai_recommendation_logs` 等 |
| 07 | [索引设计策略](./07-indexes.md) | 索引类别、查询优化、性能监控 | ✅ | UNIQUE/COMPOSITE/PARTIAL/GIN 索引 |
| 08 | [数据关系和约束](./08-relationships.md) | 外键关系、业务规则约束 | ✅ | 完整性约束、一致性规则 |
| 09 | [部署和配置](./09-deployment.md) | 数据库选择、性能调优、扩展性 | ✅ | SQLite/PostgreSQL、缓存策略 |

---

## 🗂️ 数据库表汇总

### ✅ 已实现的表（Phase 1）

#### 核心业务表
- **pt_sites** - PT站点配置（认证、同步、限流）
- **pt_resources** - PT原始资源（种子信息、促销、质量、电视剧季度/集数信息）
- **unified_movies** - 统一电影资源（元数据、评分、统计）
- **resource_mappings** - 资源映射关系（PT资源 → 统一资源）

#### 用户系统表
- **users** - 用户管理（认证、权限）
- **user_profiles** - 用户配置（下载偏好、通知设置）
- **notification_channels** - 通知渠道配置（Telegram、Email、Webhook）

#### 订阅系统表
- **subscriptions** - 订阅管理（电视剧季度订阅、资源匹配、自动下载）
- **subscription_check_logs** - 订阅检查日志（检查历史、匹配分析、动作记录）

### 🚧 待实现的表（Phase 2+）

#### 核心业务表
- **unified_tv_series** - 统一剧集资源
- **unified_music** - 统一音乐资源
- **unified_books** - 统一书籍资源
- **unified_anime** - 统一动画资源
- **unified_adult** - 统一成人内容资源
- **download_tasks** - 下载任务管理
- **media_files** - 媒体文件跟踪

#### 系统管理表
- **system_settings** - 系统配置
- **scheduled_tasks** - 调度任务模板
- **task_queue** - 任务队列

#### 日志系统表
- **sync_logs** - 同步日志
- **organize_logs** - 整理日志
- **download_logs** - 下载日志/事件
- **scan_tasks** - 扫描任务记录
- **notification_logs** - 通知日志
- **ai_recommendation_logs** - AI推荐日志

---

## 🎯 核心设计理念

### PT优先方式
以PT站点资源为数据起点，而非TMDB/豆瓣元数据，解决"无资源可用"的痛点。

### 本地缓存
定期同步PT站点资源到本地数据库，提供快速检索体验。

### 多源聚合
同一媒体的多个PT资源映射到统一资源，提供最佳下载选项。

### 媒体类型分离
为不同媒体类型（电影/剧集/音乐/书籍/动漫）设计专用表，优化查询性能。

---

## 🔍 快速查找

### 按功能查找表
- **PT站点管理** → [02-核心业务表](./02-core-tables.md#1-pt-sitespt站点配置)
- **资源同步** → [02-核心业务表](./02-core-tables.md#2-pt-resourcespt原始资源)
- **电影元数据** → [02-核心业务表](./02-core-tables.md#3-unified-movies电影资源表)
- **订阅管理** → [03-订阅系统表](./03-subscription-tables.md#1-subscriptions订阅管理)
- **订阅检查日志** → [03-订阅系统表](./03-subscription-tables.md#2-subscription_check_logs订阅检查日志)
- **用户认证** → [04-用户系统表](./04-user-tables.md#1-users用户管理)
- **通知配置** → [04-用户系统表](./04-user-tables.md#3-notification_channels通知渠道配置)

### 按开发阶段查找
- **Phase 1（已完成）** → 文档 02、04、03
- **Phase 2（计划中）** → 文档 05、06

---

## 📐 数据库架构总览

```
用户系统 (users, user_profiles, notification_channels)
    ↓
PT资源同步
    pt_sites → pt_resources → resource_mappings
                                    ↓
                          统一资源 (unified_movies, unified_tv_series, ...)
    ↓
下载管理 (download_tasks → media_files)
    ↓
订阅系统 (subscriptions → subscription_check_logs)
    ↓
AI推荐 (ai_recommendation_logs)
    ↓
通知 (notification_logs)
```

---

## 🛠️ 技术栈

- **ORM框架**：SQLAlchemy 2.0 (Async)
- **数据库**：PostgreSQL（生产） / SQLite（开发）
- **索引策略**：UNIQUE、COMPOSITE、PARTIAL、GIN（PostgreSQL）
- **数据加密**：Fernet（认证信息加密）

---

## 📝 文档维护

### 更新日志
- **2025-11-23**：订阅系统实现完成（subscriptions、subscription_check_logs），PT资源新增电视剧季度/集数识别
- **2025-11-09**：重构文档结构，按功能模块拆分为9个文档
- **2025-11-xx**：初始版本，完整数据库设计

### 贡献指南
- 更新已实现表结构时，请同步更新对应文档
- 添加新表时，请在相应章节文档中补充
- 保持文档与代码（`backend/app/models/`）一致性

---

## 🔗 相关文档

- [MTeam快速接入指南](../mteam_quick_start.md)
- [分类管理完整指南](../category_management.md)
- [元数据管理完整指南](../metadata_management.md)
- [MTeam集成详细文档](../mteam_integration_guide.md)
- [项目主文档](../../../CLAUDE.md)
