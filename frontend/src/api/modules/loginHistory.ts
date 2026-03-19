/**
 * 登录历史 API
 */

import request from '../request'
import type { LoginHistoryListResponse, LoginHistoryParams } from '@/types'

// 获取当前用户的登录历史
export function getMyLoginHistory(params?: LoginHistoryParams) {
  return request.get<LoginHistoryListResponse>('/login-history/me', { params })
}

// 获取所有用户的登录历史（管理员）
export function getAllLoginHistory(params?: LoginHistoryParams) {
  return request.get<LoginHistoryListResponse>('/login-history', { params })
}

// 清理旧登录记录（管理员）
export function cleanupLoginHistory(keepDays: number = 90) {
  return request.delete<{ message: string; deleted_count: number }>('/login-history/cleanup', {
    params: { keep_days: keepDays }
  })
}
