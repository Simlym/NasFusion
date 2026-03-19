# 订阅系统表

## 1. subscriptions（订阅管理）
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

## 2. subscription_check_logs（订阅检查日志）
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
