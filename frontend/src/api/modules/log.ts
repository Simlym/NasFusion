/**
 * 系统日志相关 API
 */

import request from '../request'
import type { ApiResponse } from '@/types/common'

export interface LogEntry {
  line_number: number
  timestamp?: string
  level?: string
  logger?: string
  message: string
  raw: string
}

export interface LogListResponse {
  items: LogEntry[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface LogFileInfo {
  file_path: string
  file_size: number
  file_size_mb: number
  line_count: number
  last_modified: number
}

export interface LogListParams {
  page?: number
  page_size?: number
  level?: string
  keyword?: string
  reverse?: boolean
}

// 获取系统日志列表
export function getSystemLogs(params?: LogListParams) {
  return request.get<LogListResponse>('/system-logs', { params })
}

// 获取日志文件信息
export function getLogFileInfo() {
  return request.get<LogFileInfo>('/system-logs/file-info')
}

// 清空系统日志
export function cleanSystemLogs() {
  return request.delete<ApiResponse<void>>('/system-logs')
}

// 日志级别相关接口
export interface LogLevelResponse {
  config_level: string
  runtime_level: string
  available_levels: string[]
}

export interface LogLevelUpdateRequest {
  level: string
}

export interface LogLevelUpdateResponse {
  success: boolean
  message: string
  config_level: string
  runtime_level: string
  note: string
}

// 获取日志级别信息
export function getLogLevel() {
  return request.get<LogLevelResponse>('/system-logs/level')
}

// 设置运行时日志级别
export function setLogLevel(level: string) {
  return request.put<LogLevelUpdateResponse>('/system-logs/level', { level })
}
