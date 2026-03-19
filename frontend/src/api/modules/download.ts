/**
 * 下载相关 API
 */

import request from '../request'
import type {
  DownloadTask,
  DownloadTaskCreate,
  DownloadTaskCreateResponse,
  DownloadTaskListResponse,
  DownloaderConfig,
  DownloaderConfigCreate,
  DownloaderConfigUpdate,
  DownloaderConfigListResponse,
  DownloadTaskAction,
  TaskStatus
} from '@/types/download'
import type { ApiResponse } from '@/types/common'

// 重新导出类型和常量
export type {
  DownloadTask,
  DownloadTaskCreate,
  DownloadTaskCreateResponse,
  DownloaderConfig,
  DownloaderConfigCreate,
  DownloaderConfigUpdate,
  DownloadTaskAction,
  TaskStatus
}

export {
  DownloaderTypeLabels,
  DownloaderStatusLabels,
  TaskStatusLabels,
  TaskStatusTypes,
  HRStrategyLabels
} from '@/types/download'

// ==================== 下载器配置 API ====================

// 获取下载器配置列表
export function getDownloaderList(params?: {
  skip?: number
  limit?: number
  is_enabled?: boolean
  type?: string
}) {
  return request.get<DownloaderConfigListResponse>('/downloaders', { params })
}

// 获取下载器配置详情
export function getDownloaderDetail(id: number) {
  return request.get<DownloaderConfig>(`/downloaders/${id}`)
}

// 创建下载器配置
export function createDownloader(data: DownloaderConfigCreate) {
  return request.post<DownloaderConfig>('/downloaders', data)
}

// 更新下载器配置
export function updateDownloader(id: number, data: DownloaderConfigUpdate) {
  return request.put<DownloaderConfig>(`/downloaders/${id}`, data)
}

// 删除下载器配置
export function deleteDownloader(id: number) {
  return request.delete(`/downloaders/${id}`)
}

// 测试下载器连接
export function testDownloaderConnection(id: number) {
  return request.post<{ success: boolean; message: string; version?: string }>(
    `/downloaders/${id}/test`
  )
}

// 获取默认下载器
export function getDefaultDownloader() {
  return request.get<DownloaderConfig>('/downloaders/default')
}

// ==================== 下载任务 API ====================

// 获取下载任务列表
export function getDownloadTaskList(params?: {
  skip?: number
  limit?: number
  status?: string
  media_type?: string
  downloader_config_id?: number
}) {
  return request.get<DownloadTaskListResponse>('/download-tasks', { params })
}

// 获取下载任务详情
export function getDownloadTaskDetail(id: number) {
  return request.get<DownloadTask>(`/download-tasks/${id}`)
}

// 创建下载任务
export function createDownloadTask(data: DownloadTaskCreate) {
  return request.post<ApiResponse<DownloadTaskCreateResponse>>('/download-tasks', data)
}

// 同步下载任务状态
export function syncDownloadTaskStatus(id: number) {
  return request.post<DownloadTask>(`/download-tasks/${id}/sync`)
}

// 控制下载任务（暂停/恢复/删除）
export function controlDownloadTask(id: number, data: DownloadTaskAction) {
  return request.post<{ success: boolean; message: string }>(`/download-tasks/${id}/action`, data)
}

// 批量同步任务状态
export async function batchSyncTasks(ids: number[]) {
  return request.post<DownloadTask[]>('/download-tasks/batch-sync', { task_ids: ids })
}
