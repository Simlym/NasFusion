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
  episode_number?: number,
  storage_mount_id?: number
) {
  return request.post<MediaFileOrganizeResponse>(`/media-files/${id}/organize`, null, {
    params: { config_id, dry_run, force, season_number, episode_number, storage_mount_id }
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

// 手动搜索豆瓣
export function searchDouban(data: { title: string; year?: number; media_type: string }) {
  return request.post<{
    results: Array<{
      douban_id: string
      title: string
      year: number | null
      overview: string | null
      poster_url: string | null
      rating_douban: number | null
      media_type: string | null
    }>
    total: number
  }>('/media-files/search-douban', data)
}

// 获取剧集文件元数据（NFO内容 + 缩略图）
export interface EpisodeMetadata {
  has_nfo: boolean
  has_poster: boolean
  poster_url: string | null
  nfo_data: Record<string, any> | null
  file_path: string | null
  organized_path: string | null
  nfo_path: string | null
  poster_file_path: string | null
  video_codec: string | null
  duration: number | null
  organized: boolean
  organize_mode: string | null
  status: string | null
  media_type: string | null
  sub_title: string | null
}

export function getEpisodeMetadata(id: number) {
  return request.get<EpisodeMetadata>(`/media-files/${id}/episode-metadata`)
}

// ==================== 刮削相关 API ====================

// 刮削单个媒体文件（下载海报、背景图、生成NFO）
export function scrapeMediaFile(id: number, config_id?: number, force = false) {
  return request.post<MediaFileScrapeResponse>(`/media-files/${id}/scrape`, {
    config_id,
    force
  })
}

// 批量刮削媒体文件
export function batchScrapeMediaFiles(data: MediaFileBatchScrapeRequest) {
  return request.post<MediaFileBatchScrapeResponse>('/media-files/batch-scrape', data)
}

// 仅生成NFO文件
export function generateNFO(id: number, config_id?: number, force = false) {
  return request.post<MediaFileGenerateNFOResponse>(`/media-files/${id}/generate-nfo`, {
    config_id,
    force
  })
}

// ==================== 文件信息编辑 API ====================

// 更新媒体文件集数信息
export function updateEpisodeInfo(id: number, data: {
  season_number?: number | null
  episode_number?: number | null
  episode_title?: string | null
}) {
  return request.put<{ success: boolean; message: string }>(`/media-files/${id}/episode-info`, data)
}

// 从文件名解析季集信息
export function parseFilename(id: number) {
  return request.get<{
    season: number | null
    episode: number | null
    title: string | null
    episode_title: string | null
    year: number | null
    resolution: string | null
  }>(`/media-files/${id}/parse-filename`)
}
