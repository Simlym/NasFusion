/**
 * 系统设置相关 API
 */

import request from '../request'
import { ApiResponse } from '@/types'

export interface SystemSetting {
  id: number
  category: string
  key: string
  value: string | null
  description: string | null
  is_active: boolean
  is_encrypted: boolean
  created_at: string
  updated_at: string
}

export interface SystemSettingCreate {
  category: string
  key: string
  value?: string | null
  description?: string | null
  is_active?: boolean
}

export interface SystemSettingUpdate {
  value?: string | null
  description?: string | null
  is_active?: boolean
}

// 获取系统设置列表
export function getSettings(category?: string) {
  return request.get<ApiResponse<{ total: number; items: SystemSetting[] }>>('/system-settings', {
    params: { category }
  })
}

// 获取单个设置
export function getSetting(category: string, key: string) {
  return request.get<ApiResponse<SystemSetting>>(`/system-settings/${category}/${key}`)
}

// 创建设置
export function createSetting(data: SystemSettingCreate) {
  return request.post<ApiResponse<SystemSetting>>('/system-settings', data)
}

// 更新设置
export function updateSetting(category: string, key: string, data: SystemSettingUpdate) {
  return request.put<ApiResponse<SystemSetting>>(`/system-settings/${category}/${key}`, data)
}

// Upsert（创建或更新）
export function upsertSetting(category: string, key: string, value: string, description?: string) {
  return request.post<ApiResponse<SystemSetting>>(
    `/system-settings/${category}/${key}/upsert`,
    null,
    {
      params: { value, description }
    }
  )
}

// 删除设置
export function deleteSetting(category: string, key: string) {
  return request.delete<ApiResponse<void>>(`/system-settings/${category}/${key}`)
}

// ================== 识别优先级配置相关 ==================

export interface IdentificationPriorityConfig {
  enabled_sources: string[]
}

/**
 * 获取资源识别优先级配置
 */
export async function getIdentificationPriority() {
  const res = await getSetting('metadata_scraping', 'identification_priority')
  const settingData = res.data?.data || res.data
  if (settingData && settingData.value) {
    const config: IdentificationPriorityConfig = JSON.parse(settingData.value)
    return {
      ...res,
      data: config
    }
  }
  // 返回默认配置
  return {
    ...res,
    data: {
      enabled_sources: ['local_cache', 'mteam_douban', 'douban_api', 'tmdb_by_imdb', 'douban_search', 'tmdb_search']
    }
  }
}

/**
 * 更新资源识别优先级配置
 */
export async function updateIdentificationPriority(enabledSources: string[]) {
  const config: IdentificationPriorityConfig = {
    enabled_sources: enabledSources
  }
  return updateSetting('metadata_scraping', 'identification_priority', {
    value: JSON.stringify(config)
  })
}
