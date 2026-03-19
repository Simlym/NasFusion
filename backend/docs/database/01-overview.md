# 系统概述和架构总览

## 1. 系统概述

### 1.1 项目简介
本系统是一个以PT站点为核心的媒体资源管理系统，解决传统"先有影评后有资源"模式的痛点。系统直接基于PT站点资源进行数据同步和管理，提供快速、便捷的媒体资源发现、下载、整理和观看体验。

### 1.2 核心理念
- **PT优先**：以PT站点资源为数据起点，而非TMDB/豆瓣等影评平台
- **本地缓存**：定期同步PT站点资源到本地数据库，提供快速检索体验
- **智能推荐**：基于用户观看历史和偏好的AI推荐系统
- **全流程管理**：从资源发现到媒体库入库的完整生命周期管理

### 1.3 技术栈
- **后端框架**：FastAPI + SQLAlchemy
- **前端框架**：Vue3 + TypeScript
- **数据库**：PostgreSQL
- **缓存**：Redis（可选）
- **AI集成**：OpenAI API（支持代理访问）

### 1.4 核心功能模块
1. **PT站点管理**：站点配置、认证、限流、健康检查
2. **资源同步系统**：全量+增量同步，多站点聚合
3. **下载管理**：多下载器支持，任务调度
4. **媒体整理**：自动文件整理、NFO生成、刮削
5. **订阅系统**：媒体状态跟踪、智能匹配
6. **智能推荐**：基于AI的个性化资源推荐
7. **通知系统**：多渠道通知、用户偏好配置

---

## 2. 数据库架构总览

### 2.1 设计原则
- **数据完整性**：通过外键约束确保数据一致性
- **查询性能**：合理的索引设计支持高效查询
- **扩展性**：JSON字段支持灵活的配置扩展
- **可维护性**：详细的日志记录支持问题排查

### 2.2 表关系概览
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

### 2.3 数据流设计
1. **同步流程**：PT站点 → pt_resources → resource_mappings → unified_resources
2. **订阅流程**：用户订阅 → 定期检查 → 资源匹配 → 通知/下载
3. **下载流程**：资源选择 → 下载任务 → 文件整理 → 媒体入库
4. **推荐流程**：用户画像 → AI分析 → 推荐生成 → 用户反馈
