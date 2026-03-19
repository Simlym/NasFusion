/**
 * 整理配置相关 API
 */

import request from '../request'
import type {
  OrganizeConfig,
  OrganizeConfigListResponse,
  OrganizeConfigCreate,
  OrganizeConfigUpdate
} from '@/types/organize'
import type { ApiResponse } from '@/types/common'

// 重新导出类型和常量
export type { OrganizeConfig, OrganizeConfigCreate, OrganizeConfigUpdate }
export { OrganizeModeLabels, NFOFormatLabels, MediaTypeLabels } from '@/types/organize'

// ==================== 整理配置 API ====================

// 获取整理配置列表
export function getOrganizeConfigList(params?: {
  skip?: number
  limit?: number
  media_type?: string
  is_enabled?: boolean
}) {
  return request.get<OrganizeConfigListResponse>('/organize-configs', { params })
}

// 获取整理配置详情
export function getOrganizeConfigDetail(id: number) {
  return request.get<OrganizeConfig>(`/organize-configs/${id}`)
}

// 获取默认配置
export function getDefaultOrganizeConfig(media_type: string) {
  return request.get<OrganizeConfig>(`/organize-configs/default/${media_type}`)
}

// 创建整理配置
export function createOrganizeConfig(data: OrganizeConfigCreate) {
  return request.post<OrganizeConfig>('/organize-configs', data)
}

// 初始化默认配置
export function initDefaultConfigs() {
  return request.post<ApiResponse>('/organize-configs/init-defaults')
}

// 更新整理配置
export function updateOrganizeConfig(id: number, data: OrganizeConfigUpdate) {
  return request.patch<OrganizeConfig>(`/organize-configs/${id}`, data)
}

// 删除整理配置
export function deleteOrganizeConfig(id: number) {
  return request.delete<ApiResponse>(`/organize-configs/${id}`)
}
