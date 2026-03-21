/**
 * PT站点相关 API
 */

import request from '../request'
import { PTSite, PTSiteForm } from '@/types'

export interface PTSiteListParams {
  page?: number
  page_size?: number
  status?: string
  sync_enabled?: boolean
}

export interface PTSiteListResponse {
  items: PTSite[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 站点预设类型
export interface SitePreset {
  id: string
  display_name: string
  description: string
  schema: string
  auth_type: string
  auth_fields: string[]
  domain: string
  icon?: string
  categories?: Record<string, string> // 分类映射：{ "401": "movie", "402": "tv", ... }
}

// 从预设创建站点的表单
export interface CreateFromPresetForm {
  preset_id: string
  auth_cookie?: string
  auth_passkey?: string
  name?: string
  domain?: string
  base_url?: string
  proxy_config?: Record<string, any>
  sync_enabled?: boolean
  sync_interval?: number
  request_interval?: number
}

// 获取PT站点列表
export function getSiteList(params?: PTSiteListParams) {
  return request.get<PTSiteListResponse>('/pt-sites', { params })
}

// 获取PT站点详情
export function getSiteDetail(id: number) {
  return request.get<PTSite>(`/pt-sites/${id}`)
}

// 创建PT站点
export function createSite(data: PTSiteForm) {
  return request.post<PTSite>('/pt-sites', data)
}

// 更新PT站点
export function updateSite(id: number, data: Partial<PTSiteForm>) {
  return request.put<PTSite>(`/pt-sites/${id}`, data)
}

// 删除PT站点
export function deleteSite(id: number) {
  return request.delete<void>(`/pt-sites/${id}`)
}

// 测试PT站点连接
export function testSiteConnection(id: number) {
  return request.post<{ success: boolean; message: string }>(`/pt-sites/${id}/test`)
}

// 刷新站点用户信息
export function refreshSiteProfile(id: number) {
  return request.post<{ success: boolean; message: string; profile: Record<string, any> | null }>(`/pt-sites/${id}/refresh-profile`)
}

// 获取站点统计信息
export function getSiteStats() {
  return request.get<
    {
      site_id: number
      site_name: string
      total_resources: number
      today_added: number
      sync_status: string
      last_sync_time?: string
      health_status: string
    }[]
  >('/pt-sites/stats')
}

// 触发站点同步
export function triggerSiteSync(id: number) {
  return request.post<{ success: boolean; message: string }>(`/pt-sites/${id}/sync`)
}

// 同步站点分类
export function syncSiteCategories(id: number) {
  return request.post<{ success: boolean; message: string }>(`/pt-sites/${id}/categories/sync`)
}

// 同步站点元数据
export function syncSiteMetadata(id: number) {
  return request.post<{ success: boolean; message: string }>(`/pt-sites/${id}/metadata/sync`)
}

// 获取站点分类列表
export function getSiteCategories(id: number) {
  return request.get<any[]>(`/pt-sites/${id}/categories`)
}

// 获取站点元数据
export function getSiteMetadata(id: number) {
  return request.get<Record<string, any>>(`/pt-sites/${id}/metadata`)
}

// ==================== 站点预设相关 API ====================

// 获取站点预设列表
export function getSitePresets() {
  return request.get<{ total: number; presets: SitePreset[] }>('/pt-sites/presets')
}

// 获取站点预设详情
export function getSitePresetDetail(presetId: string) {
  return request.get<SitePreset & Record<string, any>>(`/pt-sites/presets/${presetId}`)
}

// 获取支持的站点类型
export function getSupportedSiteTypes() {
  return request.get<{ total: number; types: string[] }>('/pt-sites/supported-types')
}

// 从预设创建站点
export function createSiteFromPreset(data: CreateFromPresetForm) {
  return request.post<PTSite>('/pt-sites/from-preset', data)
}
