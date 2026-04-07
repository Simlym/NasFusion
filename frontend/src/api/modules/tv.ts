/**
 * 电视剧资源相关 API
 */

import request from '../request'
import { UnifiedTV, UnifiedTVWithPTResources } from '@/types'
import { PaginationParams, PaginationResponse, ApiResponse } from '@/types'

export interface TVFilter {
  hasFreeResource?: boolean
  year?: number
  genre?: string
  excludeGenre?: string
  country?: string
  status?: string  // Returning Series/Ended/Canceled/In Production
  search?: string
  sortBy?: string
  order?: string
  minRating?: number
  trendingCollection?: string
  hasLocal?: boolean
}

// 电视剧更新数据接口
export interface TVUpdateData {
  // 外部ID
  tmdbId?: number | null
  imdbId?: string | null
  tvdbId?: number | null
  doubanId?: string | null
  // 标题
  title?: string
  originalTitle?: string | null
  // 基础信息
  year?: number | null
  status?: string | null  // Returning Series/Ended/Canceled/In Production
  numberOfSeasons?: number | null
  numberOfEpisodes?: number | null
  // 评分
  ratingTmdb?: number | null
  votesTmdb?: number | null
  ratingDouban?: number | null
  votesDouban?: number | null
  ratingImdb?: number | null
  votesImdb?: number | null
  // 分类
  genres?: string[] | null
  countries?: string[] | null
  languages?: string[] | null
  networks?: string[] | null
  // 内容
  overview?: string | null
  tagline?: string | null
  certification?: string | null
  // 图片
  posterUrl?: string | null
  backdropUrl?: string | null
}

// 获取电视剧列表
export function getTVList(params?: PaginationParams & TVFilter) {
  return request.get<PaginationResponse<UnifiedTV>>('/unified/tv', {
    params: {
      page: params?.page || 1,
      page_size: params?.pageSize || 20,
      has_free_resource: params?.hasFreeResource,
      year: params?.year,
      genre: params?.genre,
      exclude_genre: params?.excludeGenre,
      country: params?.country,
      status: params?.status,
      search: params?.search,
      sort_by: params?.sortBy,
      order: params?.order,
      min_rating: params?.minRating,
      trending_collection: params?.trendingCollection,
      has_local: params?.hasLocal
    }
  })
}

// 获取电视剧详情（含PT资源列表，支持分页）
export function getTVDetail(tvId: number, params?: { ptPage?: number; ptPageSize?: number }) {
  // 后端直接返回电视剧对象，不包装在 ApiResponse 中
  return request.get<UnifiedTVWithPTResources>(`/unified/tv/${tvId}`, {
    params: {
      pt_page: params?.ptPage || 1,
      pt_page_size: params?.ptPageSize || 20
    }
  })
}

// 刷新电视剧元数据
export function refreshTVMetadata(tvId: number, source: string) {
  return request.post<ApiResponse<{
    message: string
    source: string
    updatedFields: string[]
    tv: UnifiedTV
  }>>(`/unified/tv/${tvId}/refresh`, null, {
    params: { source }
  })
}

// 刷新电视剧PT资源信息（异步任务）
export function refreshTVResources(tvId: number, resourceIds?: number[]) {
  return request.post<ApiResponse<{
    executionId: number
    tvId: number
    refreshScope: string
    message: string
  }>>(`/unified/tv/${tvId}/refresh-resources`, null, {
    params: resourceIds ? { resource_ids: resourceIds } : undefined
  })
}

// 手动同步PT资源（异步任务）
export function syncTVPTResources(tvId: number, siteId?: number) {
  return request.post<ApiResponse<{
    executionId?: number
    executionIds?: number[]
    tvId: number
    keyword: string
    siteId?: number
    sitesCount?: number
    message: string
  }>>(`/unified/tv/${tvId}/sync-pt-resources`, null, {
    params: siteId ? { site_id: siteId } : undefined
  })
}

// 更新电视剧信息
export function updateTVSeries(tvId: number, data: TVUpdateData) {
  return request.put<ApiResponse<{
    message: string
    tv: UnifiedTVWithPTResources
  }>>(`/unified/tv/${tvId}`, data)
}
