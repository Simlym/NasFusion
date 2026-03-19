/**
 * 登录历史相关类型定义
 */

// 登录状态
export type LoginStatus = 'success' | 'failed' | 'locked'

// 登录历史记录
export interface LoginHistoryRecord {
  id: number
  user_id: number
  username?: string
  ip_address?: string
  user_agent?: string
  location?: string
  login_status: LoginStatus
  failure_reason?: string
  login_at: string
  created_at: string
}

// 登录历史列表响应
export interface LoginHistoryListResponse {
  items: LoginHistoryRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 登录历史查询参数
export interface LoginHistoryParams {
  page?: number
  page_size?: number
  status?: LoginStatus
  user_id?: number
}

// 登录错误详情（从后端返回）
export interface LoginErrorDetail {
  message: string
  code: 'wrong_password' | 'account_locked' | 'account_disabled'
  remaining_attempts?: number
  remaining_seconds?: number
  locked_until?: string
}
