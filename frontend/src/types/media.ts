/**
 * 媒体文件相关类型定义
 */

// 文件类型
export enum FileType {
  VIDEO = 'video',
  AUDIO = 'audio',
  SUBTITLE = 'subtitle',
  OTHER = 'other'
}

// 媒体文件状态
export enum MediaFileStatus {
  DISCOVERED = 'discovered',
  IDENTIFYING = 'identifying',
  IDENTIFIED = 'identified',
  ORGANIZING = 'organizing',
  SCRAPING = 'scraping',
  COMPLETED = 'completed',
  FAILED = 'failed',
  IGNORED = 'ignored'
}

// 匹配方法
export enum MatchMethod {
  FROM_DOWNLOAD = 'from_download',
  FROM_PT_TITLE = 'from_pt_title',
  FROM_FILENAME = 'from_filename',
  FROM_MEDIAINFO = 'from_mediainfo',
  MANUAL = 'manual',
  NONE = 'none'
}

// 媒体文件
export interface MediaFile {
  id: number
  file_path: string
  file_name: string
  directory: string
  file_size: number
  file_hash?: string
  file_type: string
  extension: string
  modified_at: string
  sub_title?: string

  // 媒体关联
  media_type: string
  unified_table_name?: string
  unified_resource_id?: number
  download_task_id?: number

  // 从下载任务继承的配置（用于整理时的默认值）
  download_organize_config_id?: number
  download_storage_mount_id?: number

  // 识别和匹配
  match_method: string
  match_confidence?: number
  match_attempts: number

  // 电视剧特定
  season_number?: number
  episode_number?: number
  episode_title?: string

  // 处理状态
  status: string
  organized: boolean
  organized_path?: string
  organized_at?: string
  organize_mode?: string

  // 技术信息
  resolution?: string
  video_codec?: string
  duration?: number
  tech_info?: any

  // 元数据
  has_subtitle: boolean
  subtitle_paths?: string[]

  // 外部集成
  // jellyfin fields removed

  // 错误追踪
  error_message?: string
  error_at?: string

  // 时间信息
  discovered_at: string
  created_at: string
  updated_at: string
}

// 媒体文件列表响应
export interface MediaFileListResponse {
  total: number
  items: MediaFile[]
}

// 扫描目录请求
export interface MediaFileScanRequest {
  directory?: string
  mount_type?: string
  recursive: boolean
  media_type?: string
  scan_mode?: 'full' | 'incremental'
}

// 整理文件请求
export interface MediaFileOrganizeRequest {
  file_ids: number[]
  config_id?: number
  dry_run: boolean
  force?: boolean  // 强制重新整理（忽略已整理状态）
  storage_mount_id?: number  // 目标存储挂载点ID（可选，不传则自动选择）
}

// 整理文件响应
export interface MediaFileOrganizeResponse {
  status: string
  message: string
  organized_path?: string
  organize_mode?: string
}

// 状态标签
export const MediaFileStatusLabels: Record<string, string> = {
  discovered: '已发现',
  identifying: '识别中',
  identified: '已识别',
  organizing: '整理中',
  scraping: '刮削中',
  completed: '已完成',
  failed: '失败',
  ignored: '已忽略'
}

// 状态类型（用于 Element Plus tag）
export const MediaFileStatusTypes: Record<string, 'success' | 'info' | 'warning' | 'danger' | ''> =
{
  discovered: 'info',
  identifying: 'info',
  identified: 'success',
  organizing: 'warning',
  scraping: 'warning',
  completed: 'success',
  failed: 'danger',
  ignored: 'info'
}

// 匹配方法标签
export const MatchMethodLabels: Record<string, string> = {
  from_download: '下载任务',
  from_pt_title: 'PT标题',
  from_filename: '文件名解析',
  from_mediainfo: 'MediaInfo',
  manual: '手动指定',
  none: '未匹配'
}

// 文件大小格式化
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 时长格式化
export function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

// ==================== 识别相关类型 ====================

// TMDB 候选项
export interface TMDBCandidate {
  tmdb_id: number
  title: string
  original_title?: string
  year?: number
  overview?: string
  poster_url?: string
  backdrop_url?: string
  rating_tmdb?: number
  votes_tmdb?: number
  genres?: string[]
  media_type: string // movie 或 tv
}

// 识别响应
export interface MediaFileIdentifyResponse {
  success: boolean
  candidates: TMDBCandidate[]
  auto_matched: boolean
  matched_id?: number
  match_source?: string
  parsed_info?: Record<string, any>
  error?: string
}

// 关联请求
export interface MediaFileLinkRequest {
  tmdb_id: number
  media_type: string
}

// 关联响应
export interface MediaFileLinkResponse {
  success: boolean
  unified_resource_id?: number
  message: string
}

// 搜索请求
export interface TMDBSearchRequest {
  title: string
  year?: number
  media_type: string
}

// 搜索响应
export interface TMDBSearchResponse {
  results: TMDBCandidate[]
  total: number
}

// ==================== 刮削相关类型 ====================

// 刮削请求
export interface MediaFileScrapeRequest {
  config_id?: number
}

// 刮削响应
export interface MediaFileScrapeResponse {
  success: boolean
  nfo_generated: boolean
  poster_downloaded: boolean
  backdrop_downloaded: boolean
  nfo_path?: string
  poster_path?: string
  backdrop_path?: string
  errors: string[]
}

// 批量刮削请求
export interface MediaFileBatchScrapeRequest {
  file_ids: number[]
  config_id?: number
}

// 批量刮削响应
export interface MediaFileBatchScrapeResponse {
  total: number
  success_count: number
  failed_count: number
  details: Record<string, any>[]
}

// 生成NFO请求
export interface MediaFileGenerateNFORequest {
  config_id?: number
}

// 生成NFO响应
export interface MediaFileGenerateNFOResponse {
  success: boolean
  nfo_path?: string
  error?: string
}
