/**
 * 榜单API模块
 */
import request from '../request'
import type { ApiResponse } from '@/types'

export interface TrendingCollectionType {
  value: string
  label: string
  mediaType: 'movie' | 'tv'
}

export interface TrendingCollectionIdsResponse {
  collection_type: string
  ids: number[]
  count: number
}

export interface TrendingSyncResponse {
  execution_id: number
  message: string
}

/**
 * 获取所有榜单类型
 */
export function getCollectionTypes() {
  return request.get<ApiResponse<{ types: TrendingCollectionType[] }>>('/trending/collections/types')
}

/**
 * 获取榜单资源ID列表
 * @param collectionType 榜单类型
 * @param limit 返回数量限制
 */
export function getCollectionIds(collectionType: string, limit?: number) {
  return request.get<ApiResponse<TrendingCollectionIdsResponse>>(
    `/trending/collections/${collectionType}/ids`,
    {
      params: { limit: limit || 100 }
    }
  )
}

/**
 * 同步榜单数据
 * @param collectionTypes 榜单类型列表（可选）
 * @param count 每个榜单同步数量
 */
export function syncCollections(collectionTypes?: string[], count?: number) {
  return request.post<ApiResponse<TrendingSyncResponse>>('/trending/sync', null, {
    params: {
      collection_types: collectionTypes,
      count: count || 100
    }
  })
}
