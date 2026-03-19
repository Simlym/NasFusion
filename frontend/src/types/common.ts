/**
 * 通用类型定义
 */

// 分页请求参数
export interface PaginationParams {
  page: number
  pageSize: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// 分页响应
export interface PaginationResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// API响应
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 统一资源表类型
export type UnifiedTableName =
  | 'unified_movies'
  | 'unified_tv_series'
  | 'unified_music'
  | 'unified_books'
  | 'unified_anime'
  | 'unified_adult'

// 媒体类型
export enum MediaType {
  MOVIE = 'movie',
  TV = 'tv',
  MUSIC = 'music',
  BOOK = 'book',
  ANIME = 'anime',
  ADULT = 'adult'
}

// 状态类型
export enum Status {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// 日期范围
export interface DateRange {
  startDate?: string
  endDate?: string
}

// 选项类型
export interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}
