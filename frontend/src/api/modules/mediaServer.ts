/**
 * 媒体服务器集成 API
 * 支持 Jellyfin/Emby/Plex
 */

import request from '../request'
import type {
  MediaServerConfig,
  MediaServerConfigCreate,
  MediaServerConfigUpdate,
  MediaServerTestConnectionResponse,
  MediaServerRefreshLibraryResponse,
  MediaServerSyncHistoryResponse,
  MediaServerLibrary,
  MediaServerStats,
  ViewingHistory,
  ViewingHistoryListResponse,
  ViewingStatisticsResponse,
  MediaServerType
} from '@/types/mediaServer'
import type { ApiResponse } from '@/types/common'

// 重新导出类型和常量
export type {
  MediaServerConfig,
  MediaServerConfigCreate,
  MediaServerConfigUpdate,
  ViewingHistory,
  MediaServerLibrary
}
export {
  MediaServerType,
  MediaServerStatus,
  MediaServerTypeLabels,
  MediaServerStatusLabels,
  MediaServerStatusTypes,
  MediaServerDefaultPorts,
  MediaServerLibraryTypeLabels,
  getServerBaseUrl,
  formatPlayProgress,
  isWatchCompleted,
  formatLastPlayed,
  getMediaTypeLabel,
  formatEpisodeInfo,
  validateServerConfig
} from '@/types/mediaServer'

// ==================== 配置管理 API ====================

/**
 * 获取媒体服务器配置列表
 * @param serverType 可选：按服务器类型过滤 (jellyfin/emby/plex)
 */
export function getMediaServerConfigs(serverType?: MediaServerType) {
  return request.get<MediaServerConfig[]>('/media-servers/configs', {
    params: serverType ? { server_type: serverType } : undefined
  })
}

/**
 * 获取配置详情
 * @param configId 配置ID
 */
export function getMediaServerConfig(configId: number) {
  return request.get<MediaServerConfig>(`/media-servers/configs/${configId}`)
}

/**
 * 创建媒体服务器配置
 * @param data 配置数据
 */
export function createMediaServerConfig(data: MediaServerConfigCreate) {
  return request.post<MediaServerConfig>('/media-servers/configs', data)
}

/**
 * 更新媒体服务器配置
 * @param configId 配置ID
 * @param data 更新数据
 */
export function updateMediaServerConfig(configId: number, data: MediaServerConfigUpdate) {
  return request.put<MediaServerConfig>(`/media-servers/configs/${configId}`, data)
}

/**
 * 删除媒体服务器配置
 * @param configId 配置ID
 */
export function deleteMediaServerConfig(configId: number) {
  return request.delete<ApiResponse>(`/media-servers/configs/${configId}`)
}

/**
 * 测试媒体服务器连接
 * @param configId 配置ID
 */
export function testMediaServerConnection(configId: number) {
  return request.post<MediaServerTestConnectionResponse>(
    `/media-servers/configs/${configId}/test`
  )
}

// ==================== 媒体库管理 API ====================

/**
 * 获取媒体库列表
 * @param configId 配置ID
 * @param includeHidden 可选：是否包含隐藏的媒体库
 */
export function getMediaServerLibraries(configId: number, includeHidden = false) {
  return request.get<MediaServerLibrary[]>(`/media-servers/${configId}/libraries`, {
    params: { include_hidden: includeHidden }
  })
}

/**
 * 刷新媒体库
 * @param configId 配置ID
 * @param libraryId 可选：指定媒体库ID，不提供则全局刷新
 */
export function refreshMediaServerLibrary(configId: number, libraryId?: string) {
  return request.post<MediaServerRefreshLibraryResponse>(
    `/media-servers/${configId}/libraries/refresh`,
    null,
    {
      params: libraryId ? { library_id: libraryId } : undefined
    }
  )
}

/**
 * 获取媒体库统计信息
 * @param configId 配置ID
 */
export function getMediaServerStats(configId: number) {
  return request.get<MediaServerStats>(`/media-servers/${configId}/stats`)
}

/**
 * 获取活动会话
 * @param configId 配置ID
 */
export function getMediaServerSessions(configId: number) {
  return request.get<any[]>(`/media-servers/${configId}/sessions`)
}

/**
 * 获取最近添加的媒体
 * @param configId 配置ID
 * @param limit 数量限制
 * @param itemType 可选类型过滤，如 'Movie' / 'Episode'
 */
export function getMediaServerLatest(configId: number, limit: number = 20, itemType?: string) {
  return request.get<any[]>(`/media-servers/${configId}/latest`, {
    params: { limit, ...(itemType && { item_type: itemType }) }
  })
}

/**
 * 获取项目详情
 * @param configId 配置ID
 * @param itemId 项目ID
 */
export function getMediaServerItem(configId: number, itemId: string) {
  return request.get<any>(`/media-servers/${configId}/items/${itemId}`)
}

/**
 * 搜索媒体
 * @param configId 配置ID
 * @param query 搜索关键词
 */
export function searchMediaServer(configId: number, query: string) {
  return request.get<any[]>(`/media-servers/${configId}/search`, {
    params: { query }
  })
}

// ==================== 观看历史 API ====================

/**
 * 获取观看历史列表
 * @param params 查询参数
 */
export function getWatchHistory(params?: {
  config_id?: number
  media_type?: string
  is_completed?: boolean
  page?: number
  page_size?: number
}) {
  return request.get<ViewingHistoryListResponse>('/media-servers/history', { params })
}

/**
 * 获取观看统计
 */
export function getWatchStatistics() {
  return request.get<ViewingStatisticsResponse>('/media-servers/history/statistics')
}

/**
 * 手动同步观看历史
 * @param configId 配置ID
 */
export function syncWatchHistory(configId: number) {
  return request.post<MediaServerSyncHistoryResponse>(
    `/media-servers/${configId}/history/sync`
  )
}

/**
 * 批量重新匹配观看历史
 * @param configId 配置ID
 * @param unmatchedOnly 是否只匹配未关联的记录
 */
export function batchRematchWatchHistory(configId: number, unmatchedOnly = false) {
  return request.post<{ execution_id: number; message: string }>(
    `/media-servers/${configId}/history/rematch`,
    null,
    {
      params: { unmatched_only: unmatchedOnly }
    }
  )
}

// ==================== 媒体库媒体项 API (本地缓存) ====================

/**
 * 获取媒体库媒体项列表（从本地数据库查询，性能优化）
 * @param configId 配置ID
 * @param params 查询参数
 */
export function getMediaServerLibraryItems(
  configId: number,
  params?: {
    media_type?: string
    item_type?: string
    item_types?: string
    library_id?: string
    has_media_file?: boolean
    has_unified_resource?: boolean
    keyword?: string
    page?: number
    page_size?: number
    order_by?: string
    order_desc?: boolean
  }
) {
  return request.get<any>(`/media-servers/${configId}/library-items`, { params })
}

/**
 * 获取剧集的所有季
 * @param configId 配置ID
 * @param seriesId 剧集的 server_item_id
 */
export function getSeriesSeasons(configId: number, seriesId: string) {
  return request.get<any>(`/media-servers/${configId}/library-items/series/${seriesId}/seasons`)
}

/**
 * 获取某一季的所有集
 * @param configId 配置ID
 * @param seriesId 剧集的 server_item_id
 * @param seasonNumber 季数
 */
export function getSeasonEpisodes(configId: number, seriesId: string, seasonNumber: number) {
  return request.get<any>(`/media-servers/${configId}/library-items/series/${seriesId}/seasons/${seasonNumber}/episodes`)
}

/**
 * 触发媒体库同步任务
 * @param configId 配置ID
 * @param params 同步参数
 */
export function syncMediaServerLibrary(
  configId: number,
  params?: {
    library_ids?: string[]
    match_files?: boolean
    sync_mode?: 'full' | 'incremental'
    incremental_hours?: number
  }
) {
  return request.post<{ execution_id: number; message: string }>(
    `/media-servers/${configId}/library-items/sync`,
    null,
    { params }
  )
}

/**
 * 获取媒体库统计信息
 * @param configId 配置ID
 */
export function getMediaServerLibraryStatistics(configId: number) {
  return request.get<any>(`/media-servers/${configId}/library-items/statistics`)
}

// ==================== 工具函数 ====================

/**
 * 批量测试连接
 * @param configIds 配置ID列表
 */
export async function batchTestConnections(configIds: number[]) {
  const results = await Promise.allSettled(
    configIds.map((id) => testMediaServerConnection(id))
  )

  return results.map((result, index) => ({
    configId: configIds[index],
    success: result.status === 'fulfilled' && result.value.data.success,
    message:
      result.status === 'fulfilled' ? result.value.data.message : (result.reason as string)
  }))
}

/**
 * 批量刷新媒体库
 * @param configIds 配置ID列表
 */
export async function batchRefreshLibraries(configIds: number[]) {
  const results = await Promise.allSettled(
    configIds.map((id) => refreshMediaServerLibrary(id))
  )

  return results.map((result, index) => ({
    configId: configIds[index],
    success: result.status === 'fulfilled' && result.value.data.success,
    message:
      result.status === 'fulfilled'
        ? result.value.data.message || '刷新成功'
        : (result.reason as string)
  }))
}

/**
 * 批量同步观看历史
 * @param configIds 配置ID列表
 */
export async function batchSyncWatchHistory(configIds: number[]) {
  const results = await Promise.allSettled(configIds.map((id) => syncWatchHistory(id)))

  return results.map((result, index) => ({
    configId: configIds[index],
    success: result.status === 'fulfilled',
    syncedCount: result.status === 'fulfilled' ? result.value.data.synced_count : 0,
    newCount: result.status === 'fulfilled' ? result.value.data.new_count : 0,
    updatedCount: result.status === 'fulfilled' ? result.value.data.updated_count : 0,
    error: result.status === 'rejected' ? (result.reason as string) : undefined
  }))
}
