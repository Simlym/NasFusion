/**
 * 订阅相关 API
 */

import request from '../request'
import type {
  Subscription,
  SubscriptionCreateForm,
  SubscriptionUpdateForm,
  SubscriptionCheckLog,
  MatchedPTResource
} from '@/types/subscription'
import type { PaginationParams, PaginationResponse, ApiResponse } from '@/types'

// 获取订阅列表
export function getSubscriptionList(params?: PaginationParams & {
  status?: string
  media_type?: string
  is_active?: boolean
}) {
  return request.get<ApiResponse<PaginationResponse<Subscription>>>('/subscriptions', { params })
}

// 获取订阅详情
export function getSubscriptionDetail(id: number) {
  return request.get<ApiResponse<Subscription>>(`/subscriptions/${id}`)
}

// 创建订阅
export function createSubscription(data: SubscriptionCreateForm) {
  return request.post<ApiResponse<Subscription>>('/subscriptions', data)
}

// 更新订阅
export function updateSubscription(id: number, data: SubscriptionUpdateForm) {
  return request.put<ApiResponse<Subscription>>(`/subscriptions/${id}`, data)
}

// 删除订阅
export function deleteSubscription(id: number) {
  return request.delete<ApiResponse<void>>(`/subscriptions/${id}`)
}

// 暂停订阅
export function pauseSubscription(id: number) {
  return request.post<ApiResponse<Subscription>>(`/subscriptions/${id}/pause`)
}

// 恢复订阅
export function resumeSubscription(id: number) {
  return request.post<ApiResponse<Subscription>>(`/subscriptions/${id}/resume`)
}

// 手动检查订阅
export function checkSubscription(id: number) {
  return request.post<ApiResponse<void>>(`/subscriptions/${id}/check`)
}

// 获取订阅匹配的PT资源
export function getMatchedResources(id: number, params?: PaginationParams) {
  return request.get<ApiResponse<PaginationResponse<MatchedPTResource>>>(
    `/subscriptions/${id}/matched-resources`,
    { params }
  )
}

// 获取订阅检查日志
export function getSubscriptionCheckLogs(id: number, params?: PaginationParams) {
  return request.get<ApiResponse<PaginationResponse<SubscriptionCheckLog>>>(
    `/subscriptions/${id}/check-logs`,
    { params }
  )
}

// 获取订阅集数状态
export function getEpisodesStatus(id: number, refresh = false) {
  return request.get<ApiResponse<any>>(`/subscriptions/${id}/episodes-status`, {
    params: { refresh }
  })
}

// 手动刷新集数状态
export function refreshEpisodesStatus(id: number) {
  return request.post<ApiResponse<any>>(`/subscriptions/${id}/episodes-status/refresh`)
}

// 手动标记集数状态
export function updateEpisodeStatus(id: number, episode: number, data: {
  status: 'downloaded' | 'ignored' | 'waiting'
  note?: string
}) {
  return request.put<ApiResponse<any>>(`/subscriptions/${id}/episodes/${episode}/status`, data)
}

// 手动同步PT资源
export function syncSubscriptionPTResources(id: number, keyword?: string, siteId?: number) {
  return request.post<ApiResponse<{
    executionId?: number
    executionIds?: number[]
    subscription_id: number
    keyword: string
    siteId?: number
    sitesCount?: number
    message: string
  }>>(`/subscriptions/${id}/sync-pt-resources`, null, {
    params: {
      site_id: siteId,
      keyword: keyword
    }
  })
}
