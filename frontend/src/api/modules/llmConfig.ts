/**
 * LLM 配置管理 API 模块
 */
import request from '../request'

// ==================== 类型定义 ====================

export interface LLMConfig {
  id: number
  name: string
  provider: string
  api_base?: string
  proxy?: string
  model: string
  default_temperature: string
  default_max_tokens: number
  default_top_p: string
  is_enabled: boolean
  sort_order: number
  last_test_at?: string
  last_test_result?: string
  created_at: string
  updated_at: string
}

export interface LLMConfigCreate {
  name: string
  provider: string
  api_key: string
  api_base?: string
  proxy?: string
  model: string
  default_temperature?: string
  default_max_tokens?: number
  default_top_p?: string
  is_enabled?: boolean
  sort_order?: number
}

export interface LLMConfigUpdate {
  name?: string
  provider?: string
  api_key?: string
  api_base?: string
  proxy?: string
  model?: string
  default_temperature?: string
  default_max_tokens?: number
  default_top_p?: string
  is_enabled?: boolean
  sort_order?: number
}

export interface LLMConfigBrief {
  id: number
  name: string
  provider: string
  model: string
  is_enabled: boolean
}

export interface ProviderTypeInfo {
  provider: string
  display_name: string
  has_predefined_models: boolean
  default_api_base: string
  models: Array<{ id: string; name: string }>
}

export interface ConnectionTestResult {
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

// ==================== API 请求 ====================

export function getLLMConfigs() {
  return request.get<LLMConfig[]>('/llm-configs')
}

export function createLLMConfig(data: LLMConfigCreate) {
  return request.post<LLMConfig>('/llm-configs', data)
}

export function updateLLMConfig(id: number, data: LLMConfigUpdate) {
  return request.put<LLMConfig>(`/llm-configs/${id}`, data)
}

export function deleteLLMConfig(id: number) {
  return request.delete(`/llm-configs/${id}`)
}

export function testLLMConfig(id: number) {
  return request.post<ConnectionTestResult>(`/llm-configs/${id}/test`)
}

export function getProviderTypes() {
  return request.get<{ providers: ProviderTypeInfo[] }>('/llm-configs/provider-types')
}
