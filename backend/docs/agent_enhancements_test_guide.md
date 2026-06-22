# AI Agent 增强功能 — 端到端测试指南

本文覆盖本轮 6 项增强的本地验证步骤。开发容器缺少运行时依赖,以下功能仅做了语法校验/逻辑模拟,**正式合并前请按此清单在本地跑通**。

## 0. 环境准备

```bash
cd backend
uv sync                      # 安装依赖(含 sqlalchemy / Pillow / httpx)
# 或: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
alembic upgrade head         # 本轮无新增模型,确保 schema 最新即可
python -m app.main           # 启动后端(http://localhost:8000/docs)
```

前置数据(让诊断类工具有东西可查):至少配置 1 个 PT 站点、同步部分资源、有若干 `media_files` 与 `download_tasks` 记录;媒体服务器(Jellyfin/Emby)接入并同步过观看历史(用于 ①)。

冒烟检查:所有工具是否注册成功(应包含 `disk_diagnose`、`media_health`):

```bash
python -c "from app.services.ai_agent import tools; from app.services.ai_agent.tool_registry import ToolRegistry; print(sorted(ToolRegistry.get_tool_names()))"
```

---

## ① 观看历史驱动推荐

**前提**:当前用户有观看历史,且观看的影片已关联到 `unified_movies`/`unified_tv_series`(`media_server_watch_histories.unified_resource_id` 非空)。

1. 对话发送:「**根据我的观影口味推荐几部电影**」
2. 预期:Agent 调用 `movie_recommend` 且 `based_on_history=true`,返回里:
   - `based_on_history: true`,`profile_genres` 为你常看的类型
   - 推荐结果**不含已看过的影片**,且偏向你的口味类型
3. 反向用例:换一个**无观看历史**的用户 → 返回 `based_on_history` 仍为 `false`,message 提示「暂无足够观看历史…已按高分热门推荐」,不报错。
4. 剧集同理:「根据我的口味推荐剧集」→ `tv_recommend` 支持 `based_on_history`。

**SQL 自查**(确认口味聚合源数据):
```sql
SELECT unified_table_name, unified_resource_id, play_count
FROM media_server_watch_histories WHERE user_id = <你的ID> AND unified_resource_id IS NOT NULL;
```

---

## ② 多模态图片识别(Telegram)

**前提**:LLM 配置为多模态模型(`gpt-4o` / `gpt-4-turbo` / `glm-4v` / `llava`);已绑定 Telegram 渠道。

1. 给 Bot **直接发一张影视剧照**(可附文字 caption,如「这是哪部剧」)
2. 预期:Bot 识别图片内容并回复(剧名/电影名 + 简介)
3. 无 caption 发图 → 使用默认提问(识别影视作品),仍能回复
4. **反向用例**:把模型切换为**非多模态**(如 `deepseek-chat`)再发图 → Bot 应提示「当前模型不支持图片识别,请切换到多模态模型」,而非静默无反应
5. Webhook 模式(`TELEGRAM_POLLING_ENABLED=false`)下重复步骤 1,确认同样生效

**日志关注**:`download_photo_as_base64` 是否成功(getFile + 下载);若 Pillow 缺失会退回原始字节但仍应可用。

---

## ③ 危险操作二次确认

**前提**:存在至少一个下载任务(记下 `task_id`)。

1. 对话:「**删除下载任务 <task_id> 并删除文件**」
2. 预期(第一段):Agent 调用 `download_manage(action=delete)`,返回 `requires_confirmation: true` + `confirmation_token` + `confirmation_prompt`;**任务未被删除**,Agent 把确认提示转达给你
3. 回复「**确认**」→ Agent 带 `__confirm__=<token>` 再次调用 → 任务真正删除
4. **反向用例**:
   - 「暂停下载任务 <task_id>」→ `pause` **不触发**确认,直接执行(可逆操作免确认)
   - 第一段拿到 token 后,改用**不同 task_id** + 旧 token 再调 → 应再次被拦截(令牌与参数绑定)
5. 安全协议存在性:确认 system prompt 含「危险操作确认协议」段落(即使自定义了 system_prompt 也应注入)

**纯逻辑回归**(无需起服务):
```bash
# 见提交 09478cf 描述,可参照其模拟脚本验证令牌派生/闸门决策
```

---

## ④ 磁盘只读诊断 `disk_diagnose`

1. 对话:「**检查一下磁盘和存储有没有问题**」或「磁盘快满了吗」
2. 预期:调用 `disk_diagnose(check=all)`,返回:
   - `storage`:各挂载点 `total/used/free_gb`、`usage_percent`、`level`
   - `broken_links`:媒体库失效链接 / 链接源丢失
   - `orphan_torrents`:种子文件丢失 / 完成数据目录丢失
   - `warnings` 汇总、`note` 提示只读
3. **造数据验证断链**:把某条已整理 `media_files` 的 `organized_path` 指向的文件手动删除/改名 → `check=broken_links` 应报出该条
4. 阈值边界:挂载点剩余 < 20GB 或使用率 ≥ 90% 应进 warnings
5. 确认**只读**:多次运行不改变任何文件/DB 记录

---

## ⑤ Watchdog 主动巡检

**前提**:Telegram 或其它通知渠道已启用(用于接收预警)。

1. 启动应用后,确认定时任务已创建:
   ```sql
   SELECT id, task_name, task_type, enabled, schedule_config
   FROM scheduled_tasks WHERE task_type = 'system_watchdog';
   ```
2. **手动触发一次**(任务管理界面点「立即执行」,或调用执行接口),观察:
   - 返回 `disk_alert_count` / `site_alert_count`
   - 若有磁盘/站点隐患 → 对应渠道收到通知
3. **造告警验证**:
   - 把某站点 `pt_sites.cookie_expire_at` 改为过去时间 → 触发 `site_auth_expired` 通知
   - 把某站点 `last_sync_status` 改为 `failed` → 触发 `site_connection_failed` 通知
   - 磁盘空间紧张的挂载点 → 触发 `disk_space_low` 通知
4. 阈值可调:修改任务 `handler_params`(`usage_warn_percent` / `free_warn_gb` / `cookie_expiry_warn_days`)后重跑生效
5. **已知取舍**:无去重/节流,持续告警会每小时重复推送(后续增强项)

---

## ⑥ 媒体库健康检查 `media_health`

1. 对话:「**媒体库有没有什么问题**」或「哪些没识别 / 缺元数据」
2. 预期:调用 `media_health(check=all)`,返回:
   - `unidentified`:未关联统一资源的媒体文件数 + 样本
   - `failed`:处理失败文件 + 错误步骤/信息
   - `low_confidence`:`match_confidence < 60` 的疑似误匹配
   - `metadata`:被引用但缺**海报/简介/评分/TMDB ID** 的电影/剧集,逐条标注缺什么
3. **造数据验证**:把某 `unified_movies` 的 `poster_url` 置空(且该电影有 media_file 引用)→ `check=metadata` 应报出并标注「海报」
4. 边界:`limit` 控制样本数(默认 20 / 上限 100),`count` 为总数
5. 与 ④ 不重叠:断链请用 `disk_diagnose`,本工具不查文件系统

---

## 回归与冒烟清单

- [ ] 已有工具未被破坏(随便调几个:`system_status`、`download_status`、`media_query`)
- [ ] `disk_diagnose` / `media_health` 出现在工具列表
- [ ] `system_watchdog` 定时任务自动创建且 enabled
- [ ] 删除类操作必须二次确认
- [ ] 多模态模型下 Telegram 发图可识别;非多模态有友好提示
- [ ] 基于历史的推荐排除已看、贴合口味
