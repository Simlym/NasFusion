/**
 * 媒体文件相关 API
 */

import request from '../request'
import type {
  MediaFile,
  MediaFileListResponse,
  MediaFileScanRequest,
  MediaFileOrganizeRequest,
  MediaFileOrganizeResponse,
  TMDBCandidate,
  MediaFileIdentifyResponse,
  MediaFileLinkRequest,
  MediaFileLinkResponse,
  TMDBSearchRequest,
  TMDBSearchResponse,
  MediaFileScrapeResponse,
  MediaFileBatchScrapeRequest,
  MediaFileBatchScrapeResponse,
  MediaFileGenerateNFOResponse
} from '@/types/media'
import type { ApiResponse } from '@/types/common'

// 重新导出类型和常量
export type { MediaFile, MediaFileScanRequest, MediaFileOrganizeRequest, TMDBCandidate }
export {
  MediaFileStatusLabels,
  MediaFileStatusTypes,
  MatchMethodLabels,
  formatFileSize,
  formatDuration
} from '@/types/media'

// ==================== 媒体文件 API ====================

// 获取媒体文件列表
export function getMediaFileList(params?: {
  skip?: number
  limit?: number
  status?: string
  media_type?: string
  organized?: boolean
  download_task_id?: number
  directory?: string
  resolution?: string
  mount_type?: string
}) {
  return request.get<MediaFileListResponse>('/media-files', { params })
}

// 获取媒体文件详情
export function getMediaFileDetail(id: number) {
  return request.get<MediaFile>(`/media-files/${id}`)
}

// 扫描目录
export function scanDirectory(data: MediaFileScanRequest) {
  return request.post<ApiResponse>('/media-files/scan', data)
}

// 提取 MediaInfo
export function extractMediaInfo(id: number) {
  return request.post<ApiResponse>(`/media-files/${id}/extract-mediainfo`)
}

// 批量整理
export function organizeMediaFiles(data: MediaFileOrganizeRequest) {
  return request.post<ApiResponse>('/media-files/organize', data)
}

// 整理单个文件
export function organizeSingleFile(
  id: number,
  config_id?: number,
  dry_run = false,
  force = false,
  season_number?: number,
  episode_number?: number
) {
  return request.post<MediaFileOrganizeResponse>(`/media-files/${id}/organize`, null, {
    params: { config_id, dry_run, force, season_number, episode_number }
  })
}

// 删除媒体文件记录
export function deleteMediaFile(id: number, delete_physical_file = false) {
  return request.delete<ApiResponse>(`/media-files/${id}`, {
    params: { delete_physical_file }
  })
}

// ==================== 识别相关 API ====================

// 识别媒体文件
export function identifyMediaFile(id: number, force_search = false) {
  return request.post<MediaFileIdentifyResponse>(`/media-files/${id}/identify`, {
    force_search
  })
}

// 关联到统一资源
export function linkMediaFileToResource(id: number, data: MediaFileLinkRequest) {
  return request.post<MediaFileLinkResponse>(`/media-files/${id}/link`, data)
}

// 手动搜索 TMDB
export function searchTMDB(data: TMDBSearchRequest) {
  return request.post<TMDBSearchResponse>('/media-files/search-tmdb', data)
}

// ==================== 刮削相关 API ====================

// 刮削单个媒体文件（下载海报、背景图、生成NFO）
export function scrapeMediaFile(id: number, config_id?: number) {
  return request.post<MediaFileScrapeResponse>(`/media-files/${id}/scrape`, {
    config_id
  })
}

// 批量刮削媒体文件
export function batchScrapeMediaFiles(data: MediaFileBatchScrapeRequest) {
  return request.post<MediaFileBatchScrapeResponse>('/media-files/batch-scrape', data)
}

// 仅生成NFO文件
export function generateNFO(id: number, config_id?: number) {
  return request.post<MediaFileGenerateNFOResponse>(`/media-files/${id}/generate-nfo`, {
    config_id
  })
}
