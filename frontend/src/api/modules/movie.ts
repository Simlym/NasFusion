/**
 * 电影资源相关 API
 */

import request from '../request'
import { UnifiedMovie, UnifiedMovieWithPTResources } from '@/types'
import { PaginationParams, PaginationResponse, ApiResponse } from '@/types'

export interface MovieFilter {
  hasFreeResource?: boolean
  year?: number
  genre?: string
  excludeGenre?: string
  country?: string
  search?: string
  search?: string
  sortBy?: string
  order?: string
  minRating?: number
  trendingCollection?: string
}

// 电影更新数据接口
export interface MovieUpdateData {
  // 外部ID
  tmdbId?: number | null
  imdbId?: string | null
  doubanId?: string | null
  // 标题
  title?: string
  originalTitle?: string | null
  // 基础信息
  year?: number | null
  runtime?: number | null
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
  // 内容
  overview?: string | null
  tagline?: string | null
  certification?: string | null
  // 图片
  posterUrl?: string | null
  backdropUrl?: string | null
}

// 获取电影列表
export function getMovieList(params?: PaginationParams & MovieFilter) {
  return request.get<PaginationResponse<UnifiedMovie>>('/unified/movies', {
    params: {
      page: params?.page || 1,
      page_size: params?.pageSize || 20,
      has_free_resource: params?.hasFreeResource,
      year: params?.year,
      genre: params?.genre,
      exclude_genre: params?.excludeGenre,
      country: params?.country,
      search: params?.search,
      sort_by: params?.sortBy,
      order: params?.order,
      min_rating: params?.minRating,
      trending_collection: params?.trendingCollection
    }
  })
}

// 获取电影详情（含PT资源列表，支持分页）
export function getMovieDetail(movieId: number, params?: { ptPage?: number; ptPageSize?: number }) {
  // 后端直接返回电影对象，不包装在 ApiResponse 中
  return request.get<UnifiedMovieWithPTResources>(`/unified/movies/${movieId}`, {
    params: {
      pt_page: params?.ptPage || 1,
      pt_page_size: params?.ptPageSize || 20
    }
  })
}

// 刷新电影元数据
export function refreshMovieMetadata(movieId: number, source: string) {
  return request.post<ApiResponse<{
    message: string
    source: string
    updatedFields: string[]
    movie: UnifiedMovie
  }>>(`/unified/movies/${movieId}/refresh`, null, {
    params: { source }
  })
}

// 刷新电影PT资源信息
export function refreshMovieResources(movieId: number) {
  return request.post<ApiResponse<{
    movieId: number
    message: string
    total: number
    success: number
    failed: number
    errors: Array<{ resource_id: number; error: string }>
  }>>(`/unified/movies/${movieId}/refresh-resources`)
}

// 手动同步PT资源（异步任务）
export function syncMoviePTResources(movieId: number, siteId?: number) {
  return request.post<ApiResponse<{
    executionId?: number
    executionIds?: number[]
    movieId: number
    keyword: string
    siteId?: number
    sitesCount?: number
    message: string
  }>>(`/unified/movies/${movieId}/sync-pt-resources`, null, {
    params: siteId ? { site_id: siteId } : undefined
  })
}

// 更新电影信息
export function updateMovie(movieId: number, data: MovieUpdateData) {
  return request.put<ApiResponse<{
    message: string
    movie: UnifiedMovieWithPTResources
  }>>(`/unified/movies/${movieId}`, data)
}
