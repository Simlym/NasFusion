/**
 * 下载相关类型定义
 */

// 下载器类型
export type DownloaderType = 'qbittorrent' | 'transmission' | 'synology_ds'

// 下载任务状态
export type TaskStatus =
  | 'pending'
  | 'downloading'
  | 'paused'
  | 'completed'
  | 'seeding'
  | 'error'
  | 'deleted'

// 下载器状态
export type DownloaderStatus = 'online' | 'offline' | 'error'

// HR处理策略
export type HRStrategy = 'none' | 'auto_limit' | 'manual'

// 分类路径配置
export interface CategoryPath {
  path: string
  is_default: boolean
}

export interface CategoryPaths {
  [category: string]: CategoryPath[]
}

// ==================== 下载器配置 ====================

export interface DownloaderConfig {
  id: number
  name: string
  type: DownloaderType
  is_default: boolean
  is_enabled: boolean
  host: string
  port: number
  username?: string
  use_ssl: boolean
  category_paths?: CategoryPaths
  hr_strategy: HRStrategy
  max_concurrent_downloads?: number
  download_speed_limit?: number
  upload_speed_limit?: number
  status: DownloaderStatus
  last_check_at?: string
  last_error?: string
  created_at: string
  updated_at: string
}

export interface DownloaderConfigCreate {
  name: string
  type: DownloaderType
  is_default?: boolean
  is_enabled?: boolean
  host: string
  port: number
  username?: string
  password?: string
  use_ssl?: boolean
  category_paths?: CategoryPaths
  hr_strategy?: HRStrategy
  max_concurrent_downloads?: number
  download_speed_limit?: number
  upload_speed_limit?: number
}

export interface DownloaderConfigUpdate {
  name?: string
  type?: DownloaderType
  is_default?: boolean
  is_enabled?: boolean
  host?: string
  port?: number
  username?: string
  password?: string
  use_ssl?: boolean
  category_paths?: CategoryPaths
  hr_strategy?: HRStrategy
  max_concurrent_downloads?: number
  download_speed_limit?: number
  upload_speed_limit?: number
}

export interface DownloaderConfigListResponse {
  total: number
  items: DownloaderConfig[]
}

// ==================== 下载任务 ====================

export interface DownloadTask {
  id: number
  task_hash: string
  pt_resource_id: number
  downloader_config_id: number
  media_type: string
  unified_table_name?: string
  unified_resource_id?: number
  client_type: DownloaderType
  client_task_id?: string
  torrent_name: string
  subtitle?: string
  save_path: string
  status: TaskStatus
  progress: number
  download_speed?: number
  upload_speed?: number
  eta?: number
  total_size: number
  downloaded_size: number
  uploaded_size: number
  ratio: number
  auto_organize: boolean
  organize_config_id?: number
  storage_mount_id?: number
  keep_seeding: boolean
  seeding_time_limit?: number
  seeding_ratio_limit?: number
  has_hr: boolean
  hr_days?: number
  hr_seed_time?: number
  hr_ratio?: number
  added_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
  error_at?: string
  retry_count: number
  created_at: string
  updated_at: string
}

export interface DownloadTaskCreate {
  pt_resource_id: number
  downloader_config_id: number
  media_type: string
  torrent_name: string
  save_path: string
  auto_organize?: boolean
  organize_config_id?: number
  storage_mount_id?: number
  keep_seeding?: boolean
  seeding_time_limit?: number
  seeding_ratio_limit?: number
  unified_table_name?: string
  unified_resource_id?: number
}

export interface DownloadTaskCreateResponse {
  id: number
  execution_id?: number
  message: string
}

export interface DownloadTaskListResponse {
  total: number
  items: DownloadTask[]
}

export interface DownloadTaskAction {
  action: 'pause' | 'resume' | 'delete'
  delete_files?: boolean
}

// ==================== 展示用的辅助类型 ====================

// 下载器类型显示名称
export const DownloaderTypeLabels: Record<DownloaderType, string> = {
  qbittorrent: 'qBittorrent',
  transmission: 'Transmission',
  synology_ds: 'Synology DSM'
}

// 任务状态显示名称
export const TaskStatusLabels: Record<TaskStatus, string> = {
  pending: '等待下载',
  downloading: '下载中',
  paused: '已暂停',
  completed: '下载完成',
  seeding: '做种中',
  error: '错误',
  deleted: '已删除'
}

// 任务状态标签类型
export const TaskStatusTypes: Record<TaskStatus, 'info' | 'success' | 'warning' | 'danger'> = {
  pending: 'info',
  downloading: 'warning',
  paused: 'info',
  completed: 'success',
  seeding: 'success',
  error: 'danger',
  deleted: 'info'
}

// 下载器状态显示名称
export const DownloaderStatusLabels: Record<DownloaderStatus, string> = {
  online: '在线',
  offline: '离线',
  error: '错误'
}

// HR策略显示名称
export const HRStrategyLabels: Record<HRStrategy, string> = {
  none: '不处理',
  auto_limit: '自动设置做种限制',
  manual: '手动处理'
}
