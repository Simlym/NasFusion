/**
 * 用户相关类型定义
 */

// 用户角色
export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest'
}

// 用户
export interface User {
  id: number
  username: string
  email?: string
  role: UserRole
  is_active: boolean
  is_verified: boolean
  display_name?: string
  avatar_url?: string
  timezone: string
  language: string
  last_login_at?: string
  created_at: string
  updated_at: string
  profile?: UserProfile
}

// 用户配置
export interface UserProfile {
  id: number
  user_id: number
  ui_theme: 'light' | 'dark' | 'ocean' | 'auto'
  language: string
  timezone: string
  items_per_page: number
  min_seeders: number
  max_auto_download_size_gb?: number
  default_downloader?: string
  auto_start_download: boolean
  download_path_template?: string
  notification_enabled: boolean
  email_notifications: boolean
  push_notifications: boolean
  ai_recommendations_enabled: boolean
  recommendation_frequency: string
  share_anonymous_stats: boolean
  public_watchlist: boolean
  created_at: string
  updated_at: string
}

// 登录表单
export interface LoginForm {
  username: string
  password: string
  remember?: boolean
}

// 登录响应
export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token?: string
}

// 用户统计
export interface UserStats {
  totalUsers: number
  activeUsers: number
  totalSubscriptions: number
  totalDownloads: number
}
