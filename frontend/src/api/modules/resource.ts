/**
 * 资源相关 API
 */

import request from '../request'
import { PTResource, UnifiedResourceBase, ResourceFilter } from '@/types'
import { PaginationParams, PaginationResponse, ApiResponse } from '@/types'

export interface PTResourceFilter {
  siteId?: number
  category?: string
  originalCategoryId?: string
  isFree?: boolean
  minSeeders?: number
  resolution?: string
  videoCodec?: string
  videoSource?: string
  search?: string
  hasMapping?: boolean
  identificationStatus?: string
  subscriptionId?: number
}

// 获取PT资源列表
export function getPTResourceList(params?: PaginationParams & PTResourceFilter) {
  return request.get<ApiResponse<PaginationResponse<PTResource>>>('/pt-resources', {
    params: {
      page: params?.page || 1,
      page_size: params?.pageSize || 20,
      site_id: params?.siteId,
      category: params?.category,
      original_category_id: params?.originalCategoryId,
      is_free: params?.isFree,
      min_seeders: params?.minSeeders,
      resolution: params?.resolution,
      video_codec: params?.videoCodec,
      video_source: params?.videoSource,
      search: params?.search,
      has_mapping: params?.hasMapping,
      identification_status: params?.identificationStatus,
      subscription_id: params?.subscriptionId
    }
  })
}

// 获取PT资源详情
export function getPTResourceDetail(resourceId: number) {
  return request.get<ApiResponse<PTResource>>(`/pt-resources/${resourceId}`)
}

// 获取资源完整详情（调用PT站点API）
export function fetchPTResourceDetail(resourceId: number) {
  return request.post<ApiResponse<PTResource>>(`/pt-resources/${resourceId}/fetch-detail`)
}

// 删除PT资源
export function deletePTResource(resourceId: number) {
  return request.delete<ApiResponse<void>>(`/pt-resources/${resourceId}`)
}

// 同步站点资源
export interface SyncRequest {
  syncType: 'full' | 'incremental' | 'manual'
  maxPages?: number
  startPage?: number
}

export function syncSiteResources(siteId: number, data: SyncRequest) {
  return request.post<ApiResponse<any>>(`/pt-resources/sites/${siteId}/sync`, data)
}

// 获取统一资源列表
export function getUnifiedResourceList(params?: PaginationParams & ResourceFilter) {
  return request.get<ApiResponse<PaginationResponse<UnifiedResourceBase>>>('/resources/unified', {
    params
  })
}

// 获取资源详情
export function getResourceDetail(tableName: string, id: number) {
  return request.get<ApiResponse<UnifiedResourceBase>>(`/resources/unified/${tableName}/${id}`)
}

// 获取资源关联的PT资源
export function getResourcePTSources(tableName: string, id: number) {
  return request.get<ApiResponse<PTResource[]>>(`/resources/unified/${tableName}/${id}/pt-sources`)
}

// 搜索资源
export function searchResources(keyword: string, params?: ResourceFilter) {
  return request.get<ApiResponse<PaginationResponse<UnifiedResourceBase>>>('/resources/search', {
    params: { keyword, ...params }
  })
}

// 刷新资源元数据
export function refreshResourceMetadata(tableName: string, id: number) {
  return request.post<ApiResponse<void>>(`/resources/unified/${tableName}/${id}/refresh`)
}

// 批量重置识别状态
export function batchResetIdentificationStatus(resourceIds: number[]) {
  return request.post<ApiResponse<{ count: number }>>('/pt-resources/batch-reset-identification-status', resourceIds)
}
