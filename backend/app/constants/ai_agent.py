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
ZHIPU_MODEL_GLM_5 = "glm-5"
ZHIPU_MODEL_GLM_5_1 = "glm-5.1"
ZHIPU_MODEL_GLM_5_TURBO = "glm-5-turbo"
# GLM-4.8 系列
ZHIPU_MODEL_GLM_4_8 = "glm-4.8"
# GLM-4.7 系列
ZHIPU_MODEL_GLM_4_7 = "glm-4.7"
ZHIPU_MODEL_GLM_4_7V = "glm-4.7v"
# GLM-4.6 系列（Claude Code 编程）
ZHIPU_MODEL_GLM_4_6 = "glm-4.6"
# GLM-Z1 推理模型系列
ZHIPU_MODEL_GLM_Z1_FLASH = "glm-z1-flash"
ZHIPU_MODEL_GLM_Z1_AIR = "glm-z1-air"
ZHIPU_MODEL_GLM_Z1_AIRX = "glm-z1-airx"
# GLM-4 系列
ZHIPU_MODEL_GLM_4_PLUS = "glm-4-plus"
ZHIPU_MODEL_GLM_4_AIR = "glm-4-air"
ZHIPU_MODEL_GLM_4_AIRX = "glm-4-airx"
ZHIPU_MODEL_GLM_4_FLASH = "glm-4-flash"
ZHIPU_MODEL_GLM_4_FLASHX = "glm-4-flashx"
ZHIPU_MODEL_GLM_4_LONG = "glm-4-long"
ZHIPU_MODEL_GLM_4 = "glm-4"

ZHIPU_MODELS = [
    ZHIPU_MODEL_GLM_5_1,
    ZHIPU_MODEL_GLM_5,
    ZHIPU_MODEL_GLM_5_TURBO,
    ZHIPU_MODEL_GLM_4_8,
    ZHIPU_MODEL_GLM_4_7,
    ZHIPU_MODEL_GLM_4_7V,
    ZHIPU_MODEL_GLM_4_6,
    ZHIPU_MODEL_GLM_Z1_FLASH,
    ZHIPU_MODEL_GLM_Z1_AIR,
    ZHIPU_MODEL_GLM_Z1_AIRX,
    ZHIPU_MODEL_GLM_4_PLUS,
    ZHIPU_MODEL_GLM_4_AIR,
    ZHIPU_MODEL_GLM_4_AIRX,
    ZHIPU_MODEL_GLM_4_FLASH,
    ZHIPU_MODEL_GLM_4_FLASHX,
    ZHIPU_MODEL_GLM_4_LONG,
    ZHIPU_MODEL_GLM_4,
]

ZHIPU_MODEL_DISPLAY_NAMES = {
    ZHIPU_MODEL_GLM_5_1: "GLM-5.1 (最新旗舰·Claude Code)",
    ZHIPU_MODEL_GLM_5: "GLM-5 (旗舰)",
    ZHIPU_MODEL_GLM_5_TURBO: "GLM-5-Turbo (旗舰·快速)",
    ZHIPU_MODEL_GLM_4_8: "GLM-4.8 (编程增强)",
    ZHIPU_MODEL_GLM_4_7: "GLM-4.7 (旗舰)",
    ZHIPU_MODEL_GLM_4_7V: "GLM-4.7V (多模态)",
    ZHIPU_MODEL_GLM_4_6: "GLM-4.6 (Claude Code 编程)",
    ZHIPU_MODEL_GLM_Z1_FLASH: "GLM-Z1-Flash (推理·快速)",
    ZHIPU_MODEL_GLM_Z1_AIR: "GLM-Z1-Air (推理·轻量)",
    ZHIPU_MODEL_GLM_Z1_AIRX: "GLM-Z1-AirX (推理·极速)",
    ZHIPU_MODEL_GLM_4_PLUS: "GLM-4-Plus (增强)",
    ZHIPU_MODEL_GLM_4_AIR: "GLM-4-Air (轻量)",
    ZHIPU_MODEL_GLM_4_AIRX: "GLM-4-AirX (轻量·极速)",
    ZHIPU_MODEL_GLM_4_FLASH: "GLM-4-Flash (快速·免费)",
    ZHIPU_MODEL_GLM_4_FLASHX: "GLM-4-FlashX (快速·增强)",
    ZHIPU_MODEL_GLM_4_LONG: "GLM-4-Long (长文本)",
    ZHIPU_MODEL_GLM_4: "GLM-4 (标准)",
}

# ===== Kimi 模型 (月之暗面) =====
KIMI_MODEL_K2_5 = "kimi-k2.5"
KIMI_MODEL_K2 = "kimi-k2"
KIMI_MODEL_K2_THINKING = "kimi-k2-thinking"
KIMI_MODEL_MOONSHOT_V1_AUTO = "moonshot-v1-auto"
KIMI_MODEL_MOONSHOT_V1_128K = "moonshot-v1-128k"
KIMI_MODEL_MOONSHOT_V1_32K = "moonshot-v1-32k"
KIMI_MODEL_MOONSHOT_V1_8K = "moonshot-v1-8k"

KIMI_MODELS = [
    KIMI_MODEL_K2_5,
    KIMI_MODEL_K2,
    KIMI_MODEL_K2_THINKING,
    KIMI_MODEL_MOONSHOT_V1_AUTO,
    KIMI_MODEL_MOONSHOT_V1_128K,
    KIMI_MODEL_MOONSHOT_V1_32K,
    KIMI_MODEL_MOONSHOT_V1_8K,
]

KIMI_MODEL_DISPLAY_NAMES = {
    KIMI_MODEL_K2_5: "Kimi K2.5 (最新旗舰·Claude Code)",
    KIMI_MODEL_K2: "Kimi K2 (编程)",
    KIMI_MODEL_K2_THINKING: "Kimi K2 Thinking (推理)",
    KIMI_MODEL_MOONSHOT_V1_AUTO: "Moonshot V1 Auto (自动)",
    KIMI_MODEL_MOONSHOT_V1_128K: "Moonshot V1 128K (长文本)",
    KIMI_MODEL_MOONSHOT_V1_32K: "Moonshot V1 32K",
    KIMI_MODEL_MOONSHOT_V1_8K: "Moonshot V1 8K",
}

# ===== 供应商类型信息 =====
LLM_PROVIDER_TYPE_INFO = {
    LLM_PROVIDER_ZHIPU: {
        "has_predefined_models": True,
        "default_api_base": "https://open.bigmodel.cn/api/paas/v4",
    },
    LLM_PROVIDER_OPENAI: {
        "has_predefined_models": False,
        "default_api_base": "https://api.openai.com/v1",
    },
    LLM_PROVIDER_DEEPSEEK: {
        "has_predefined_models": False,
        "default_api_base": "https://api.deepseek.com/v1",
    },
    LLM_PROVIDER_ANTHROPIC: {
        "has_predefined_models": False,
        "default_api_base": "https://api.anthropic.com/v1",
    },
    LLM_PROVIDER_QWEN: {
        "has_predefined_models": False,
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
DEFAULT_ZHIPU_MODEL = ZHIPU_MODEL_GLM_5
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
