/**
 * AI Agent API 模块
 */
import request from '../request'

// ==================== 类型定义 ====================

export interface LLMProviderModel {
  id: string
  name: string
}

export interface LLMProvider {
  provider: string
  display_name: string
  models: LLMProviderModel[]
  supports_tools: boolean
  supports_streaming: boolean
}

export interface AIAgentConfig {
  id: number
  user_id: number
  llm_config_id?: number | null
  llm_config_name?: string | null
  provider: string
  api_base?: string
  proxy?: string
  model: string
  temperature: string
  max_tokens: number
  top_p: string
  is_enabled: boolean
  enable_tools: boolean
  enable_streaming: boolean
  status: string
  last_test_at?: string
  last_test_result?: string
  system_prompt?: string
  created_at: string
  updated_at: string
}

export interface AIAgentConfigCreate {
  llm_config_id?: number | null
  provider?: string
  api_key?: string
  api_base?: string
  proxy?: string
  model?: string
  temperature?: string
  max_tokens?: number
  top_p?: string
  is_enabled?: boolean
  enable_tools?: boolean
  enable_streaming?: boolean
  system_prompt?: string
}

export interface AIAgentConfigUpdate {
  llm_config_id?: number | null
  provider?: string
  api_key?: string
  api_base?: string
  proxy?: string
  model?: string
  temperature?: string
  max_tokens?: number
  top_p?: string
  is_enabled?: boolean
  enable_tools?: boolean
  enable_streaming?: boolean
  system_prompt?: string
}

export interface AIConversation {
  id: number
  user_id: number
  title?: string
  source: string
  telegram_chat_id?: string
  status: string
  message_count: number
  last_message_at?: string
  context_summary?: string
  created_at: string
  updated_at: string
}

export interface AIMessage {
  id: number
  conversation_id: number
  role: string
  content?: string
  tool_calls?: any[]
  tool_call_id?: string
  tool_name?: string
  prompt_tokens?: number
  completion_tokens?: number
  model?: string
  finish_reason?: string
  created_at: string
}

export interface AIConversationDetail extends AIConversation {
  messages: AIMessage[]
}

export interface AIChatRequest {
  message: string
  conversation_id?: number
  stream?: boolean
}

export interface AIChatResponse {
  conversation_id: number
  message_id: number
  content: string
  tool_calls?: any[]
  tool_results?: any[]
  finish_reason: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export interface AIConnectionTestRequest {
  provider: string
  api_key: string
  api_base?: string
  proxy?: string
  model?: string
}

export interface AIConnectionTestResponse {
  success: boolean
  message: string
  latency_ms: number
  model?: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export interface AITool {
  name: string
  description: string
  parameters: any
}

export interface LLMConfigOption {
  id: number
  name: string
  provider: string
  model: string
  is_enabled: boolean
}

// ==================== API 请求 ====================

/**
 * 获取支持的LLM供应商列表
 */
export function getProviders() {
  return request.get<{ providers: LLMProvider[] }>('/ai-agent/providers')
}

/**
 * 获取AI Agent配置
 */
export function getConfig() {
  return request.get<AIAgentConfig | null>('/ai-agent/config')
}

/**
 * 创建AI Agent配置
 */
export function createConfig(data: AIAgentConfigCreate) {
  return request.post<AIAgentConfig>('/ai-agent/config', data)
}

/**
 * 更新AI Agent配置
 */
export function updateConfig(data: AIAgentConfigUpdate) {
  return request.put<AIAgentConfig>('/ai-agent/config', data)
}

/**
 * 测试LLM连接
 */
export function testConnection(data: AIConnectionTestRequest) {
  return request.post<AIConnectionTestResponse>('/ai-agent/config/test', data)
}

/**
 * 获取对话列表
 */
export function getConversations(params?: {
  page?: number
  page_size?: number
  status?: string
}) {
  return request.get<{
    items: AIConversation[]
    total: number
    page: number
    page_size: number
  }>('/ai-agent/conversations', { params })
}

/**
 * 创建新对话
 */
export function createConversation(data?: {
  title?: string
  source?: string
}) {
  return request.post<AIConversation>('/ai-agent/conversations', data || {})
}

/**
 * 获取对话详情
 */
export function getConversation(conversationId: number) {
  return request.get<AIConversationDetail>(`/ai-agent/conversations/${conversationId}`)
}

/**
 * 更新对话
 */
export function updateConversation(conversationId: number, data: {
  title?: string
  status?: string
}) {
  return request.put<AIConversation>(`/ai-agent/conversations/${conversationId}`, data)
}

/**
 * 删除对话
 */
export function deleteConversation(conversationId: number) {
  return request.delete(`/ai-agent/conversations/${conversationId}`)
}

/**
 * 发送聊天消息
 */
export function chat(data: AIChatRequest) {
  return request.post<AIChatResponse>('/ai-agent/chat', data)
}

/**
 * 流式聊天（返回 EventSource URL）
 */
export function getChatStreamUrl() {
  return '/ai-agent/chat/stream'
}

/**
 * 获取可用工具列表
 */
export function getTools() {
  return request.get<{ tools: AITool[] }>('/ai-agent/tools')
}

/**
 * 获取已启用的全局 LLM 配置列表（给 AI 助手选择用）
 */
export function getLLMOptions() {
  return request.get<LLMConfigOption[]>('/ai-agent/llm-options')
}
