/**
 * 媒体文件 API
 */
import request from './request'

/**
 * 媒体文件对象
 */
export interface MediaFile {
  id: number
  file_path: string
  file_name: string
  directory: string
  file_size: number
  file_type: string
  extension: string
  modified_at: string
  media_type: string
  unified_table_name: string | null
  unified_resource_id: number | null
  download_task_id: number | null
  media_directory_id: number | null
  match_method: string
  match_confidence: number | null
  status: string
  organized: boolean
  organized_path: string | null
  organized_at: string | null
  resolution: string | null
  has_nfo: boolean
  has_poster: boolean
  has_subtitle: boolean
  season_number: number | null
  episode_number: number | null
  episode_title: string | null
  created_at: string
  updated_at: string
}

/**
 * 媒体文件列表响应
 */
export interface MediaFileListResponse {
  items: MediaFile[]
  total: number
  page: number
  page_size: number
}

/**
 * 扫描请求参数
 */
export interface ScanMediaFilesRequest {
  directory: string
  scan_mode?: 'full' | 'incremental'
  media_type?: string | null
}

/**
 * 扫描响应
 */
export interface ScanMediaFilesResponse {
  execution_id: number
  message: string
}

/**
 * 获取媒体文件列表
 */
export function getMediaFiles(params?: {
  skip?: number
  limit?: number
  media_type?: string
  status?: string
  organized?: boolean
  directory?: string
}) {
  return request.get<MediaFileListResponse>('/media-files', { params })
}

/**
 * 获取媒体文件详情
 */
export function getMediaFile(id: number) {
  return request.get<MediaFile>(`/media-files/${id}`)
}

/**
 * 扫描媒体文件
 */
export function scanMediaFiles(data: ScanMediaFilesRequest) {
  return request.post<ScanMediaFilesResponse>('/media-files/scan', data)
}

/**
 * 删除媒体文件记录
 */
export function deleteMediaFile(id: number) {
  return request.delete(`/media-files/${id}`)
}

/**
 * 批量删除媒体文件记录
 */
export function batchDeleteMediaFiles(ids: number[]) {
  return request.post('/media-files/batch-delete', { ids })
}

/**
 * 更新媒体文件
 */
export function updateMediaFile(id: number, data: Partial<MediaFile>) {
  return request.put<MediaFile>(`/media-files/${id}`, data)
}
