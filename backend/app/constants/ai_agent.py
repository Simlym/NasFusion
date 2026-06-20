# -*- coding: utf-8 -*-
"""
AI Agent 相关常量
"""

# ===== LLM 供应商类型 =====
LLM_PROVIDER_ZHIPU = "zhipu"
LLM_PROVIDER_OPENAI = "openai"
LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_DEEPSEEK = "deepseek"
LLM_PROVIDER_QWEN = "qwen"
LLM_PROVIDER_KIMI = "kimi"

LLM_PROVIDERS = [
    LLM_PROVIDER_ZHIPU,
    LLM_PROVIDER_OPENAI,
    LLM_PROVIDER_ANTHROPIC,
    LLM_PROVIDER_DEEPSEEK,
    LLM_PROVIDER_QWEN,
    LLM_PROVIDER_KIMI,
]

LLM_PROVIDER_DISPLAY_NAMES = {
    LLM_PROVIDER_ZHIPU: "智谱AI",
    LLM_PROVIDER_OPENAI: "OpenAI",
    LLM_PROVIDER_ANTHROPIC: "Anthropic",
    LLM_PROVIDER_DEEPSEEK: "DeepSeek",
    LLM_PROVIDER_QWEN: "通义千问",
    LLM_PROVIDER_KIMI: "Kimi (月之暗面)",
}

# ===== 智谱模型 =====
# GLM-5 系列（最新一代）
ZHIPU_MODEL_GLM_5_1 = "glm-5.1"
ZHIPU_MODEL_GLM_5_TURBO = "glm-5-turbo"

ZHIPU_MODELS = [
    ZHIPU_MODEL_GLM_5_1,
    ZHIPU_MODEL_GLM_5_TURBO,
]

ZHIPU_MODEL_DISPLAY_NAMES = {
    ZHIPU_MODEL_GLM_5_1: "GLM-5.1 (最新旗舰·Claude Code)",
    ZHIPU_MODEL_GLM_5_TURBO: "GLM-5-Turbo (旗舰·快速)",
}

# ===== Kimi 模型 (月之暗面) =====
KIMI_MODEL_K2_6 = "kimi-k2.6"
KIMI_MODEL_K2_THINKING = "kimi-k2-thinking"

KIMI_MODELS = [
    KIMI_MODEL_K2_6,
    KIMI_MODEL_K2_THINKING,
]

KIMI_MODEL_DISPLAY_NAMES = {
    KIMI_MODEL_K2_6: "Kimi K2.6 (最新旗舰·Claude Code)",
    KIMI_MODEL_K2_THINKING: "Kimi K2 Thinking (推理)",
}

# ===== OpenAI 模型 =====
OPENAI_MODEL_GPT_4_1 = "gpt-4.1"
OPENAI_MODEL_GPT_4_1_MINI = "gpt-4.1-mini"
OPENAI_MODEL_GPT_4_1_NANO = "gpt-4.1-nano"
OPENAI_MODEL_GPT_4O = "gpt-4o"
OPENAI_MODEL_GPT_4O_MINI = "gpt-4o-mini"
OPENAI_MODEL_O3 = "o3"
OPENAI_MODEL_O3_MINI = "o3-mini"
OPENAI_MODEL_O4_MINI = "o4-mini"

OPENAI_MODELS = [
    OPENAI_MODEL_GPT_4_1,
    OPENAI_MODEL_GPT_4_1_MINI,
    OPENAI_MODEL_GPT_4_1_NANO,
    OPENAI_MODEL_GPT_4O,
    OPENAI_MODEL_GPT_4O_MINI,
    OPENAI_MODEL_O3,
    OPENAI_MODEL_O3_MINI,
    OPENAI_MODEL_O4_MINI,
]

OPENAI_MODEL_DISPLAY_NAMES = {
    OPENAI_MODEL_GPT_4_1: "GPT-4.1 (最新旗舰)",
    OPENAI_MODEL_GPT_4_1_MINI: "GPT-4.1 Mini (轻量)",
    OPENAI_MODEL_GPT_4_1_NANO: "GPT-4.1 Nano (极速·低成本)",
    OPENAI_MODEL_GPT_4O: "GPT-4o (多模态)",
    OPENAI_MODEL_GPT_4O_MINI: "GPT-4o Mini (轻量·多模态)",
    OPENAI_MODEL_O3: "O3 (推理旗舰)",
    OPENAI_MODEL_O3_MINI: "O3 Mini (推理·轻量)",
    OPENAI_MODEL_O4_MINI: "O4 Mini (推理·最新)",
}

# ===== Anthropic 模型 =====
ANTHROPIC_MODEL_CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
ANTHROPIC_MODEL_CLAUDE_HAIKU_4 = "claude-haiku-4-20250414"
ANTHROPIC_MODEL_CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
ANTHROPIC_MODEL_CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
ANTHROPIC_MODEL_CLAUDE_3_OPUS = "claude-3-opus-20240229"

ANTHROPIC_MODELS = [
    ANTHROPIC_MODEL_CLAUDE_SONNET_4,
    ANTHROPIC_MODEL_CLAUDE_HAIKU_4,
    ANTHROPIC_MODEL_CLAUDE_3_5_SONNET,
    ANTHROPIC_MODEL_CLAUDE_3_5_HAIKU,
    ANTHROPIC_MODEL_CLAUDE_3_OPUS,
]

ANTHROPIC_MODEL_DISPLAY_NAMES = {
    ANTHROPIC_MODEL_CLAUDE_SONNET_4: "Claude Sonnet 4 (最新旗舰)",
    ANTHROPIC_MODEL_CLAUDE_HAIKU_4: "Claude Haiku 4 (轻量·快速)",
    ANTHROPIC_MODEL_CLAUDE_3_5_SONNET: "Claude 3.5 Sonnet (平衡)",
    ANTHROPIC_MODEL_CLAUDE_3_5_HAIKU: "Claude 3.5 Haiku (极速·低成本)",
    ANTHROPIC_MODEL_CLAUDE_3_OPUS: "Claude 3 Opus (强力)",
}

# ===== DeepSeek 模型 =====
DEEPSEEK_MODEL_CHAT = "deepseek-chat"
DEEPSEEK_MODEL_REASONER = "deepseek-reasoner"

DEEPSEEK_MODELS = [
    DEEPSEEK_MODEL_CHAT,
    DEEPSEEK_MODEL_REASONER,
]

DEEPSEEK_MODEL_DISPLAY_NAMES = {
    DEEPSEEK_MODEL_CHAT: "DeepSeek V4 (通用对话)",
    DEEPSEEK_MODEL_REASONER: "DeepSeek V4 (推理·思考模式)",
}

# ===== 通义千问 模型 =====
QWEN_MODEL_QWEN3_235B = "qwen3-235b-a22b"
QWEN_MODEL_QWEN3_30B = "qwen3-30b-a3b"
QWEN_MODEL_QWEN3_32B = "qwen3-32b"
QWEN_MODEL_QWEN3_14B = "qwen3-14b"
QWEN_MODEL_QWEN3_8B = "qwen3-8b"
QWEN_MODEL_QWEN3_CODER_PLUS = "qwen3-coder-plus"
QWEN_MODEL_QWEN_MAX = "qwen-max"
QWEN_MODEL_QWEN_PLUS = "qwen-plus"
QWEN_MODEL_QWEN_TURBO = "qwen-turbo"
QWEN_MODEL_QWEN_LONG = "qwen-long"

QWEN_MODELS = [
    QWEN_MODEL_QWEN3_235B,
    QWEN_MODEL_QWEN3_30B,
    QWEN_MODEL_QWEN3_32B,
    QWEN_MODEL_QWEN3_14B,
    QWEN_MODEL_QWEN3_8B,
    QWEN_MODEL_QWEN3_CODER_PLUS,
    QWEN_MODEL_QWEN_MAX,
    QWEN_MODEL_QWEN_PLUS,
    QWEN_MODEL_QWEN_TURBO,
    QWEN_MODEL_QWEN_LONG,
]

QWEN_MODEL_DISPLAY_NAMES = {
    QWEN_MODEL_QWEN3_235B: "Qwen3 235B-A22B (旗舰·MoE)",
    QWEN_MODEL_QWEN3_30B: "Qwen3 30B-A3B (轻量·MoE)",
    QWEN_MODEL_QWEN3_32B: "Qwen3 32B (Dense)",
    QWEN_MODEL_QWEN3_14B: "Qwen3 14B (中等)",
    QWEN_MODEL_QWEN3_8B: "Qwen3 8B (轻量)",
    QWEN_MODEL_QWEN3_CODER_PLUS: "Qwen3 Coder Plus (编程)",
    QWEN_MODEL_QWEN_MAX: "Qwen Max (旗舰)",
    QWEN_MODEL_QWEN_PLUS: "Qwen Plus (增强)",
    QWEN_MODEL_QWEN_TURBO: "Qwen Turbo (快速)",
    QWEN_MODEL_QWEN_LONG: "Qwen Long (长文本)",
}

# ===== 供应商类型信息 =====
LLM_PROVIDER_TYPE_INFO = {
    LLM_PROVIDER_ZHIPU: {
        "has_predefined_models": True,
        "default_api_base": "https://open.bigmodel.cn/api/paas/v4",
    },
    LLM_PROVIDER_OPENAI: {
        "has_predefined_models": True,
        "default_api_base": "https://api.openai.com/v1",
    },
    LLM_PROVIDER_DEEPSEEK: {
        "has_predefined_models": True,
        "default_api_base": "https://api.deepseek.com/v1",
    },
    LLM_PROVIDER_ANTHROPIC: {
        "has_predefined_models": True,
        "default_api_base": "https://api.anthropic.com/v1",
    },
    LLM_PROVIDER_QWEN: {
        "has_predefined_models": True,
        "default_api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    LLM_PROVIDER_KIMI: {
        "has_predefined_models": True,
        "default_api_base": "https://api.moonshot.cn/v1",
    },
}

# ===== Agent 工具类型 =====
AGENT_TOOL_MOVIE_RECOMMEND = "movie_recommend"
AGENT_TOOL_TV_RECOMMEND = "tv_recommend"
AGENT_TOOL_PT_SYNC = "pt_sync"
AGENT_TOOL_RESOURCE_SEARCH = "resource_search"
AGENT_TOOL_RESOURCE_IDENTIFY = "resource_identify"
AGENT_TOOL_DOWNLOAD_CREATE = "download_create"
AGENT_TOOL_DOWNLOAD_STATUS = "download_status"
AGENT_TOOL_SUBSCRIPTION_CREATE = "subscription_create"
AGENT_TOOL_SUBSCRIPTION_LIST = "subscription_list"
AGENT_TOOL_SUBSCRIPTION_UPDATE = "subscription_update"
AGENT_TOOL_SUBSCRIPTION_DELETE = "subscription_delete"
AGENT_TOOL_MEDIA_QUERY = "media_query"
AGENT_TOOL_SYSTEM_STATUS = "system_status"
AGENT_TOOL_TRENDING_QUERY = "trending_query"
AGENT_TOOL_DOWNLOAD_MANAGE = "download_manage"
AGENT_TOOL_TASK_MANAGE = "task_manage"
AGENT_TOOL_SETTINGS_MANAGE = "settings_manage"

AGENT_TOOLS = [
    AGENT_TOOL_MOVIE_RECOMMEND,
    AGENT_TOOL_TV_RECOMMEND,
    AGENT_TOOL_PT_SYNC,
    AGENT_TOOL_RESOURCE_SEARCH,
    AGENT_TOOL_RESOURCE_IDENTIFY,
    AGENT_TOOL_DOWNLOAD_CREATE,
    AGENT_TOOL_DOWNLOAD_STATUS,
    AGENT_TOOL_DOWNLOAD_MANAGE,
    AGENT_TOOL_SUBSCRIPTION_CREATE,
    AGENT_TOOL_SUBSCRIPTION_LIST,
    AGENT_TOOL_SUBSCRIPTION_UPDATE,
    AGENT_TOOL_SUBSCRIPTION_DELETE,
    AGENT_TOOL_MEDIA_QUERY,
    AGENT_TOOL_SYSTEM_STATUS,
    AGENT_TOOL_TRENDING_QUERY,
    AGENT_TOOL_TASK_MANAGE,
    AGENT_TOOL_SETTINGS_MANAGE,
]

AGENT_TOOL_DISPLAY_NAMES = {
    AGENT_TOOL_MOVIE_RECOMMEND: "电影推荐",
    AGENT_TOOL_TV_RECOMMEND: "剧集推荐",
    AGENT_TOOL_PT_SYNC: "PT资源同步",
    AGENT_TOOL_RESOURCE_SEARCH: "资源搜索",
    AGENT_TOOL_RESOURCE_IDENTIFY: "资源识别",
    AGENT_TOOL_DOWNLOAD_CREATE: "创建下载",
    AGENT_TOOL_DOWNLOAD_STATUS: "下载状态",
    AGENT_TOOL_DOWNLOAD_MANAGE: "下载管理",
    AGENT_TOOL_SUBSCRIPTION_CREATE: "创建订阅",
    AGENT_TOOL_SUBSCRIPTION_LIST: "订阅列表",
    AGENT_TOOL_SUBSCRIPTION_UPDATE: "修改订阅",
    AGENT_TOOL_SUBSCRIPTION_DELETE: "删除订阅",
    AGENT_TOOL_MEDIA_QUERY: "媒体库查询",
    AGENT_TOOL_SYSTEM_STATUS: "系统状态",
    AGENT_TOOL_TRENDING_QUERY: "榜单查询",
    AGENT_TOOL_TASK_MANAGE: "任务管理",
    AGENT_TOOL_SETTINGS_MANAGE: "系统设置",
}

# ===== 对话消息角色 =====
MESSAGE_ROLE_SYSTEM = "system"
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_ROLE_TOOL = "tool"

MESSAGE_ROLES = [
    MESSAGE_ROLE_SYSTEM,
    MESSAGE_ROLE_USER,
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_TOOL,
]

# ===== 对话状态 =====
CONVERSATION_STATUS_ACTIVE = "active"
CONVERSATION_STATUS_ARCHIVED = "archived"
CONVERSATION_STATUS_DELETED = "deleted"

CONVERSATION_STATUSES = [
    CONVERSATION_STATUS_ACTIVE,
    CONVERSATION_STATUS_ARCHIVED,
    CONVERSATION_STATUS_DELETED,
]

# ===== Agent 配置状态 =====
AGENT_CONFIG_STATUS_ENABLED = "enabled"
AGENT_CONFIG_STATUS_DISABLED = "disabled"
AGENT_CONFIG_STATUS_ERROR = "error"

AGENT_CONFIG_STATUSES = [
    AGENT_CONFIG_STATUS_ENABLED,
    AGENT_CONFIG_STATUS_DISABLED,
    AGENT_CONFIG_STATUS_ERROR,
]

# ===== 意图类型 =====
INTENT_RECOMMEND = "recommend"
INTENT_SEARCH = "search"
INTENT_DOWNLOAD = "download"
INTENT_SUBSCRIBE = "subscribe"
INTENT_QUERY = "query"
INTENT_SYNC = "sync"
INTENT_IDENTIFY = "identify"
INTENT_CHAT = "chat"
INTENT_UNKNOWN = "unknown"

INTENTS = [
    INTENT_RECOMMEND,
    INTENT_SEARCH,
    INTENT_DOWNLOAD,
    INTENT_SUBSCRIBE,
    INTENT_QUERY,
    INTENT_SYNC,
    INTENT_IDENTIFY,
    INTENT_CHAT,
    INTENT_UNKNOWN,
]

INTENT_DISPLAY_NAMES = {
    INTENT_RECOMMEND: "推荐",
    INTENT_SEARCH: "搜索",
    INTENT_DOWNLOAD: "下载",
    INTENT_SUBSCRIBE: "订阅",
    INTENT_QUERY: "查询",
    INTENT_SYNC: "同步",
    INTENT_IDENTIFY: "识别",
    INTENT_CHAT: "闲聊",
    INTENT_UNKNOWN: "未知",
}

# ===== 交互来源 =====
INTERACTION_SOURCE_WEB = "web"
INTERACTION_SOURCE_TELEGRAM = "telegram"
INTERACTION_SOURCE_API = "api"

INTERACTION_SOURCES = [
    INTERACTION_SOURCE_WEB,
    INTERACTION_SOURCE_TELEGRAM,
    INTERACTION_SOURCE_API,
]

# ===== 默认配置 =====
DEFAULT_LLM_PROVIDER = LLM_PROVIDER_ZHIPU
DEFAULT_ZHIPU_MODEL = ZHIPU_MODEL_GLM_5_1
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_CONVERSATION_MAX_TURNS = 20
DEFAULT_CONTEXT_WINDOW = 8000

# ===== API 配置 =====
ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
ZHIPU_API_TIMEOUT = 60  # 秒

# ===== 系统提示词 =====
DEFAULT_SYSTEM_PROMPT = """你是 NasFusion 的智能助手，专门帮助用户管理媒体资源。你可以：

1. **电影/剧集推荐**：根据用户的喜好推荐电影或电视剧
2. **资源搜索**：在 PT 站点搜索特定的影视资源
3. **资源识别**：识别文件名对应的影视作品信息
4. **下载管理**：创建下载任务、查询下载状态
5. **订阅管理**：创建追剧订阅、查看订阅列表
6. **媒体库查询**：查询本地媒体库中的内容
7. **榜单查询**：查看豆瓣、TMDB 热门榜单
8. **系统设置**：查看和修改系统配置，查看各模块的配置状态。模块包括：系统配置、存储管理、PT站点、下载器、媒体服务器、整理规则、媒体刮削、通知设置、登录安全

请用简洁友好的中文回复用户。当需要执行具体操作时，我会调用相应的工具来完成。
对于系统设置的修改，请在执行前向用户确认变更内容。"""
