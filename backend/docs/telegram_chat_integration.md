# Telegram 对话接入

将 AI Agent 接入 Telegram，实现与 Web 端一致的对话能力。Web 端对话见 `AIAgent.vue` + `/api/v1/ai-agent/chat`。

## 两种消息接收方式

| 方式 | 是否需要公网 | 说明 | 启用 |
|------|------------|------|------|
| **长轮询（默认）** | 否 | 应用主动 `getUpdates` 拉取消息，内网/NAS 即可工作 | `TELEGRAM_POLLING_ENABLED=true`（默认） |
| Webhook | 是（HTTPS） | Telegram 主动推送到 `/api/v1/telegram/webhook/<token>` | 设 `TELEGRAM_POLLING_ENABLED=false` 并手动配置 Webhook |

两者复用同一套处理逻辑（`telegram_handler.process_telegram_update`），二选一即可——长轮询启动时会自动 `deleteWebhook`，避免 409 冲突。

## 工作流程

1. 应用启动（`main.py` lifespan）调用 `telegram_polling_manager.start()`
2. 从**已启用的 Telegram 通知渠道**读取 `bot_token`，每个唯一 token 启动一个轮询协程
3. 用户给 Bot 发消息 → 长轮询拉到 → `TelegramAgentHandler` 调用 `AIAgentService.chat()` → 回复
4. 每个 chat 维持一条持续对话（`get_or_create_telegram_conversation`），多轮上下文连贯
5. 通知渠道增删改时，API 层调用 `telegram_polling_manager.reload()` 热更新，无需重启

## 用户配置步骤

1. 找 [@BotFather](https://t.me/BotFather) 创建 Bot，拿到 `bot_token`
2. 给自己的 Bot 发送 `/start`，Bot 会回复你的 **Chat ID**
3. 在系统「通知渠道」中新建 Telegram 渠道，填入 `bot_token` 和 `chat_id`，启用
4. 直接给 Bot 发消息即可对话（如「推荐几部科幻电影」「查看下载状态」）

## 代理

内网访问 Telegram API 受限时，在「通知设置 → 全局设置 → Telegram 代理地址」配置代理
（支持 http/socks5），收发消息（长轮询、对话回复、通知发送、连接测试）全链路共用。

代理存储于系统设置 `category='notification', key='telegram_proxy'`，与 TMDB 代理同样的
管理方式：Web 可配、热生效、各服务代理互不影响。读取逻辑见 `telegram_proxy.py`。

## 消息格式（Markdown → Telegram）

AI 输出的是通用 Markdown，Telegram 不支持表格等语法，直接发会显示成原始文本。
回复发送前用 `telegramify-markdown` 的 `standardize()` 转换为 Telegram MarkdownV2：

- 表格 → ` ``` ` 等宽代码块（手机端对齐显示）
- `**加粗**` → `*加粗*`、`*斜体*` → `_斜体_`、`# 标题`、有序/无序列表等正确渲染

转换在 `TelegramAgentHandler.send_reply` 中完成；若 MarkdownV2 解析失败（实体不合法等），
自动降级为纯文本重发，保证消息可达。

> 注意：工具调用后 `AIAgentService` 已让 LLM 二次生成完整回复，handler **不再**手动拼接
> 工具结果摘要，避免与 AI 回复内容重复。

## 相关文件

- `app/services/ai_agent/telegram_polling.py` — 长轮询服务（轮询器 + 管理器单例）
- `app/services/ai_agent/telegram_handler.py` — 消息处理与回复
- `app/api/v1/telegram_webhook.py` — Webhook 端点（备用方式）
- `app/api/v1/notification_channels.py` — 渠道增删改时触发 `reload()`
