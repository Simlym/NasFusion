/**
 * 媒体服务器集成相关类型定义
 * 支持 Jellyfin/Emby/Plex
 */

// ==================== 枚举类型 ====================

// 媒体服务器类型
export enum MediaServerType {
  JELLYFIN = 'jellyfin',
  EMBY = 'emby',
  PLEX = 'plex'
}

// 媒体服务器状态
export enum MediaServerStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  ERROR = 'error'
}

// 媒体库类型
export enum MediaServerLibraryType {
  MOVIES = 'movies',
  TVSHOWS = 'tvshows',
  MUSIC = 'music',
  BOOKS = 'books'
}

// ==================== 配置相关类型 ====================

// 媒体服务器配置
export interface MediaServerConfig {
  id: number
  user_id: number
  type: MediaServerType
  name: string
  host: string
  port: number
  use_ssl: boolean
  is_default: boolean

  // 功能开关
  auto_refresh_library: boolean
  sync_watch_history: boolean
  watch_history_sync_interval: number

  // 状态信息
  status: MediaServerStatus
  last_check_at?: string
  last_sync_at?: string
  last_error?: string
  server_config?: Record<string, any>

  // 认证信息已设置标志（用于编辑时判断）
  has_api_key?: boolean
  has_token?: boolean
  has_password?: boolean

  // 时间戳
  created_at: string
  updated_at: string
}

// 创建媒体服务器配置请求
export interface MediaServerConfigCreate {
  type: MediaServerType
  name: string
  host: string
  port: number
  use_ssl?: boolean

  // 认证信息（根据服务器类型选择使用）
  api_key?: string  // Jellyfin/Emby
  token?: string    // Plex
  username?: string
  password?: string

  // 服务器特定配置
  server_config?: Record<string, any>

  // 功能开关
  is_default?: boolean
  auto_refresh_library?: boolean
  sync_watch_history?: boolean
  watch_history_sync_interval?: number

  // 路径映射
  library_path_mappings?: Array<{ server_path: string; local_path: string }>
}

// 更新媒体服务器配置请求
export interface MediaServerConfigUpdate {
  name?: string
  host?: string
  port?: number
  use_ssl?: boolean
  api_key?: string
  token?: string
  username?: string
  password?: string
  server_config?: Record<string, any>
  is_default?: boolean
  auto_refresh_library?: boolean
  sync_watch_history?: boolean
  watch_history_sync_interval?: number
  library_path_mappings?: Array<{ server_path: string; local_path: string }>
}

// 连接测试响应
export interface MediaServerTestConnectionResponse {
  success: boolean
  message: string
}

// ==================== 观看历史相关类型 ====================

// 观看历史
export interface ViewingHistory {
  id: number
  user_id: number
  media_server_config_id: number
  server_type: MediaServerType
  server_item_id: string

  // 媒体信息
  media_type: string  // movie/tv/music
  title: string
  year?: number

  // 电视剧特定信息
  season_number?: number
  episode_number?: number
  episode_title?: string

  // 播放信息
  play_count: number
  last_played_at: string
  play_duration_seconds?: number
  runtime_seconds?: number
  is_completed: boolean

  // 额外扩展字段
  server_name?: string
  image_url?: string
  playback_url?: string
  playback_progress?: number

  // 本地文件关联
  media_file_id?: number
  unified_table_name?: string
  unified_resource_id?: number
  unified_id?: number

  // 时间戳
  created_at: string
  updated_at: string
}

// 观看历史列表响应
export interface ViewingHistoryListResponse {
  items: ViewingHistory[]
  total: number
  page: number
  page_size: number
}

// 观看统计响应
export interface ViewingStatisticsResponse {
  total_count: number
  completed_count: number
  by_type: Record<string, number>
}

// 同步观看历史响应
export interface MediaServerSyncHistoryResponse {
  synced_count: number
  new_count: number
  updated_count: number
}

// ==================== 媒体库相关类型 ====================

// 媒体库
export interface MediaServerLibrary {
  id: string
  name: string
  type: string
  locations: string[]
  image_url?: string
  web_url?: string
  item_count?: number
  last_scan_at?: string
}

// 刷新媒体库响应
export interface MediaServerRefreshLibraryResponse {
  success: boolean
  message?: string
}

// 媒体库统计
export interface MediaServerStats {
  stats_data: Record<string, any>
  movie_count: number
  tv_count: number
  episode_count: number
  user_count: number
}

// ==================== 标签和常量 ====================

// 服务器类型标签
export const MediaServerTypeLabels: Record<MediaServerType, string> = {
  [MediaServerType.JELLYFIN]: 'Jellyfin',
  [MediaServerType.EMBY]: 'Emby',
  [MediaServerType.PLEX]: 'Plex'
}

// 服务器状态标签
export const MediaServerStatusLabels: Record<MediaServerStatus, string> = {
  [MediaServerStatus.ONLINE]: '在线',
  [MediaServerStatus.OFFLINE]: '离线',
  [MediaServerStatus.ERROR]: '错误'
}

// 状态类型（用于 Element Plus tag）
export const MediaServerStatusTypes: Record<
  MediaServerStatus,
  'success' | 'info' | 'warning' | 'danger' | 'primary'
> = {
  [MediaServerStatus.ONLINE]: 'success',
  [MediaServerStatus.OFFLINE]: 'info',
  [MediaServerStatus.ERROR]: 'danger'
}

// 默认端口
export const MediaServerDefaultPorts: Record<MediaServerType, number> = {
  [MediaServerType.JELLYFIN]: 8096,
  [MediaServerType.EMBY]: 8096,
  [MediaServerType.PLEX]: 32400
}

// 媒体库类型标签
export const MediaServerLibraryTypeLabels: Record<string, string> = {
  movies: '电影',
  tvshows: '剧集',
  music: '音乐',
  books: '图书',
  mixed: '混合'
}

// ==================== 工具函数 ====================

/**
 * 获取服务器基础 URL
 */
export function getServerBaseUrl(config: MediaServerConfig | MediaServerConfigCreate): string {
  const protocol = config.use_ssl ? 'https' : 'http'
  return `${protocol}://${config.host}:${config.port}`
}

/**
 * 格式化播放进度
 */
export function formatPlayProgress(
  playDuration?: number,
  runtime?: number
): { progress: number; text: string } {
  if (!playDuration || !runtime || runtime === 0) {
    return { progress: 0, text: '未播放' }
  }

  const progress = Math.round((playDuration / runtime) * 100)
  const hours = Math.floor(playDuration / 3600)
  const minutes = Math.floor((playDuration % 3600) / 60)

  let text = ''
  if (hours > 0) {
    text = `已播放 ${hours}小时${minutes}分钟`
  } else {
    text = `已播放 ${minutes}分钟`
  }

  return { progress: Math.min(progress, 100), text }
}

/**
 * 判断是否看完（>90%）
 */
export function isWatchCompleted(playDuration?: number, runtime?: number): boolean {
  if (!playDuration || !runtime || runtime === 0) return false
  return playDuration / runtime >= 0.9
}

/**
 * 格式化观看时间
 */
export function formatLastPlayed(lastPlayedAt: string): string {
  const date = new Date(lastPlayedAt)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}天前`
  if (hours > 0) return `${hours}小时前`
  if (minutes > 0) return `${minutes}分钟前`
  return '刚刚'
}

/**
 * 获取媒体类型中文名称
 */
export function getMediaTypeLabel(mediaType: string): string {
  const labels: Record<string, string> = {
    movie: '电影',
    tv: '剧集',
    episode: '剧集',
    music: '音乐',
    book: '图书'
  }
  return labels[mediaType] || mediaType
}

/**
 * 格式化电视剧集信息
 */
export function formatEpisodeInfo(
  seasonNumber?: number,
  episodeNumber?: number,
  episodeTitle?: string
): string {
  if (!seasonNumber || !episodeNumber) return ''

  const seasonEp = `S${seasonNumber.toString().padStart(2, '0')}E${episodeNumber
    .toString()
    .padStart(2, '0')}`

  return episodeTitle ? `${seasonEp} - ${episodeTitle}` : seasonEp
}

/**
 * 验证服务器配置
 */
export function validateServerConfig(config: MediaServerConfigCreate): string[] {
  const errors: string[] = []

  if (!config.name || config.name.trim() === '') {
    errors.push('配置名称不能为空')
  }

  if (!config.host || config.host.trim() === '') {
    errors.push('服务器地址不能为空')
  }

  if (!config.port || config.port < 1 || config.port > 65535) {
    errors.push('端口号必须在 1-65535 之间')
  }

  // 根据服务器类型验证认证信息
  if (config.type === MediaServerType.JELLYFIN || config.type === MediaServerType.EMBY) {
    if (!config.api_key || config.api_key.trim() === '') {
      errors.push(`${MediaServerTypeLabels[config.type]} 需要提供 API Key`)
    }
  } else if (config.type === MediaServerType.PLEX) {
    if (!config.token || config.token.trim() === '') {
      errors.push('Plex 需要提供访问令牌（Token）')
    }
  }

  return errors
}
