/**
 * 媒体目录 API
 */
import request from './request'
import type { TMDBSearchResponse } from '@/types/media'

/**
 * 目录树节点
 */
export interface DirectoryTreeNode {
  id: number
  directory_name: string
  directory_path: string
  parent_id: number | null
  media_type: string | null
  unified_table_name: string | null
  unified_resource_id: number | null
  series_name: string | null
  season_number: number | null
  episode_count: number
  has_nfo: boolean
  nfo_path: string | null
  has_poster: boolean
  poster_path: string | null
  has_backdrop: boolean
  backdrop_path: string | null
  issue_flags: Record<string, any>
  total_files: number
  total_size: number
  scanned_at: string | null
  created_at: string
  updated_at: string
  has_issues: boolean
  children?: DirectoryTreeNode[]
  subdir_count?: number
}

/**
 * NFO 数据
 */
export interface NFOData {
  type?: string
  title?: string
  original_title?: string
  plot?: string
  outline?: string
  tagline?: string
  rating?: number
  year?: number
  runtime?: number
  premiered?: string
  releasedate?: string
  genres?: string[]
  tags?: string[]
  studios?: string[]
  studio?: string
  countries?: string[]
  directors?: string[]
  director?: string
  writers?: string[]
  actors?: Array<{
    name: string
    role?: string
    thumb?: string
  }>
  poster?: string
  fanart?: string
  imdb_id?: string
  tmdb_id?: string
  tvdb_id?: string
  // Episode specific fields
  season?: number
  episode?: number
  aired?: string
  // TV Show specific fields
  status?: string
}

/**
 * 目录详情响应
 */
export interface DirectoryDetailResponse {
  directory: DirectoryTreeNode
  statistics: {
    total_files: number
    total_size: number
    video_files: number
    identified_files: number
  }
  files: any[]
  nfo_data?: NFOData | null
  unified_resource?: {
    id: number
    title: string
    original_title?: string | null
    year?: number | null
    poster_url?: string | null
    backdrop_url?: string | null
    rating?: number | null
    genres?: string[] | null
    overview?: string | null
    media_type?: string
  } | null
}

/**
 * 获取目录树
 */
export function getDirectoryTree(params?: {
  media_type?: string
  parent_id?: number | null
  load_children?: boolean
  issues?: string[]
}) {
  return request.get<DirectoryTreeNode[]>('/media-directories/tree', {
    params: {
      ...params,
      // 数组参数序列化需要处理，这里假设 axios 或 request 库已配置好，或者后端能解析
      // 如果后端 FastAPI 使用 Query(default=None) list 接收，这里直接传数组即可
    }
  })
}

/**
 * 获取目录信息
 */
export function getDirectory(id: number) {
  return request.get<DirectoryTreeNode>(`/media-directories/${id}`)
}

/**
 * 获取目录详情（含文件列表）
 */
export function getDirectoryDetail(id: number) {
  return request.get<DirectoryDetailResponse>(`/media-directories/${id}/detail`)
}

/**
 * 同步目录树（从文件构建）
 */
export function syncDirectories(data: { base_directory: string }) {
  return request.post<{ created: number; updated: number }>('/media-directories/sync', data)
}

/**
 * 检测目录问题
 */
export function detectIssues(data?: { directory_id?: number | null; media_type?: string | null }) {
  return request.post<{ issues: Record<string, number>; total_issues: number }>(
    '/media-directories/detect-issues',
    data || {}
  )
}

/**
 * 关联目录到统一资源（通过TMDB/豆瓣ID 或 直接关联已有资源）
 */
export function linkDirectoryToResource(id: number, data: {
  tmdb_id?: number | null
  douban_id?: string | null
  media_type?: string
  unified_table_name?: string | null
  unified_resource_id?: number | null
}) {
  return request.put<{
    success: boolean
    unified_resource_id: number
    unified_table_name: string
    title: string | null
    message: string
  }>(`/media-directories/${id}/link`, data)
}

/**
 * 搜索TMDB（用于目录识别关联）
 */
export function searchTMDBForDirectory(data: { title: string; year?: number; media_type: string }) {
  return request.post<TMDBSearchResponse>('/media-files/search-tmdb', data)
}

/**
 * 删除目录记录
 */
export function deleteDirectory(id: number) {
  return request.delete(`/media-directories/${id}`)
}
