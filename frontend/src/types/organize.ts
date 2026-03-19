/**
 * 整理配置相关类型定义
 */

// 整理模式
export enum OrganizeMode {
  HARDLINK = 'hardlink',
  REFLINK = 'reflink',
  SYMLINK = 'symlink',
  MOVE = 'move',
  COPY = 'copy'
}

// NFO格式
export enum NFOFormat {
  JELLYFIN = 'jellyfin',
  EMBY = 'emby',
  PLEX = 'plex',
  KODI = 'kodi'
}

// 整理配置
export interface OrganizeConfig {
  id: number
  name: string
  media_type: string
  library_root: string
  dir_template: string
  filename_template: string
  organize_mode: string
  is_enabled: boolean
  is_default: boolean
  description?: string

  // NFO和元数据配置
  generate_nfo: boolean
  nfo_format: string
  download_poster: boolean
  download_backdrop: boolean
  poster_filename: string
  backdrop_filename: string

  // 字幕配置
  organize_subtitles: boolean
  subtitle_filename_template?: string

  // 文件过滤
  min_file_size_mb?: number
  max_file_size_mb?: number
  include_extensions?: string[]
  exclude_extensions?: string[]
  exclude_keywords?: string[]

  // 高级选项
  skip_existed: boolean
  overwrite_nfo: boolean
  overwrite_poster: boolean
  overwrite_backdrop: boolean

  // 字幕下载
  auto_download_subtitle: boolean
  subtitle_languages?: string[]

  // 通知配置
  notify_on_success: boolean
  notify_on_failure: boolean

  // 统计信息
  total_organized_count: number
  last_organized_at?: string

  // 时间信息
  created_at: string
  updated_at: string
}

// 整理配置列表响应
export interface OrganizeConfigListResponse {
  total: number
  items: OrganizeConfig[]
}

// 创建整理配置
export interface OrganizeConfigCreate {
  name: string
  media_type: string
  library_root: string
  dir_template: string
  filename_template: string
  organize_mode?: string
  is_enabled?: boolean
  is_default?: boolean
  description?: string

  generate_nfo?: boolean
  nfo_format?: string
  download_poster?: boolean
  download_backdrop?: boolean
  poster_filename?: string
  backdrop_filename?: string

  organize_subtitles?: boolean
  subtitle_filename_template?: string

  min_file_size_mb?: number
  max_file_size_mb?: number
  include_extensions?: string[]
  exclude_extensions?: string[]
  exclude_keywords?: string[]

  skip_existed?: boolean
  overwrite_nfo?: boolean
  overwrite_poster?: boolean
  overwrite_backdrop?: boolean

  auto_download_subtitle?: boolean
  subtitle_languages?: string[]

  notify_on_success?: boolean
  notify_on_failure?: boolean
}

// 更新整理配置
export interface OrganizeConfigUpdate {
  name?: string
  is_enabled?: boolean
  is_default?: boolean
  library_root?: string
  dir_template?: string
  filename_template?: string
  organize_mode?: string
  generate_nfo?: boolean
  nfo_format?: string
  download_poster?: boolean
  download_backdrop?: boolean
  organize_subtitles?: boolean
  skip_existed?: boolean
  description?: string
}

// 整理模式标签
export const OrganizeModeLabels: Record<string, string> = {
  hardlink: '硬链接（推荐）',
  reflink: 'Reflink（Btrfs推荐）',
  symlink: '软链接',
  move: '移动文件',
  copy: '复制文件'
}

// NFO格式标签
export const NFOFormatLabels: Record<string, string> = {
  jellyfin: 'Jellyfin',
  emby: 'Emby',
  plex: 'Plex',
  kodi: 'Kodi'
}

// 媒体类型标签
export const MediaTypeLabels: Record<string, string> = {
  movie: '电影',
  tv: '电视剧',
  anime: '动漫',
  music: '音乐',
  book: '电子书',
  adult: '成人内容'
}
