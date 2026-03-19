/**
 * 任务调度相关 API
 */

import request from '../request'
import {
  ScheduledTask,
  ScheduledTaskCreate,
  ScheduledTaskListResponse,
  PTSyncTaskCreate,
  TaskExecutionListResponse,
  TaskQueueStatus
} from '@/types'

export interface ScheduledTaskListParams {
  skip?: number
  limit?: number
  enabled_only?: boolean
  task_type?: string
  keyword?: string
}

export interface TaskExecutionListParams {
  page?: number
  page_size?: number
  task_type?: string
  status?: string
  scheduled_task_id?: number
  keyword?: string
  start_date?: string
  end_date?: string
  sort_by?: string
  sort_order?: string
}

// 获取调度任务列表
export function getScheduledTasks(params?: ScheduledTaskListParams) {
  return request.get<ScheduledTaskListResponse>('/scheduled-tasks', { params })
}

// 获取调度任务详情
export function getScheduledTask(id: number) {
  return request.get<ScheduledTask>(`/scheduled-tasks/${id}`)
}

// 创建调度任务
export function createScheduledTask(data: ScheduledTaskCreate) {
  return request.post<ScheduledTask>('/scheduled-tasks', data)
}

// 创建PT同步任务（快捷方式）
export function createPTSyncTask(data: PTSyncTaskCreate) {
  return request.post<ScheduledTask>('/scheduled-tasks/pt-sync', data)
}

// 更新调度任务
export function updateScheduledTask(id: number, data: Partial<ScheduledTaskCreate>) {
  return request.put<ScheduledTask>(`/scheduled-tasks/${id}`, data)
}

// 删除调度任务
export function deleteScheduledTask(id: number) {
  return request.delete<void>(`/scheduled-tasks/${id}`)
}

// 切换任务启用状态
export function toggleScheduledTask(id: number) {
  return request.post<ScheduledTask>(`/scheduled-tasks/${id}/toggle`)
}

// 立即执行任务
export function runScheduledTaskNow(id: number, handlerParams?: Record<string, any>) {
  return request.post<{ message: string; execution_id: number }>(
    `/scheduled-tasks/${id}/run`,
    handlerParams ? { handler_params: handlerParams } : {}
  )
}

// 获取任务执行历史
export function getTaskExecutions(taskId: number, params?: TaskExecutionListParams) {
  return request.get<TaskExecutionListResponse>(`/scheduled-tasks/${taskId}/executions`, { params })
}

// 获取任务队列状态
export function getTaskQueueStatus() {
  return request.get<TaskQueueStatus>('/task-executions/queue/status')
}

// 获取单个任务执行详情
export function getTaskExecution(executionId: number) {
  return request.get(`/task-executions/${executionId}`)
}

// 获取全部执行历史列表（支持过滤、分页、排序）
export function getTaskExecutionsList(params?: TaskExecutionListParams) {
  return request.get<TaskExecutionListResponse>('/task-executions', { params })
}

// 取消任务执行
export function cancelTaskExecution(executionId: number) {
  return request.post(`/task-executions/${executionId}/cancel`)
}
