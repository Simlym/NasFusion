import request from '../request'

export interface TaskExecutionSummary {
    id: number
    task_name: string
    task_type: string
    status: string
    progress: number
    created_at: string
    started_at?: string
    completed_at?: string
    updated_at?: string
    duration?: number
    handler_params?: any
    error_message?: string
}

import type { ViewingHistory } from './mediaServer'

export interface MediaBackdropItem {
    id: number
    media_type: 'movie' | 'tv'
    title: string
    year?: number
    backdrop_url: string
    poster_url?: string
    rating?: number
    overview?: string
}

export interface DashboardStatsResponse {
    // 发现
    total_sites: number
    total_resources: number
    total_movies: number
    total_tvs: number
    total_actors: number
    today_new_resources: number
    today_new_movies: number
    today_new_tvs: number
    today_updated_tvs: number
    today_new_actors: number
    // 媒体
    total_subscriptions: number
    today_new_subscriptions: number
    total_downloads: number
    active_downloads: number
    today_new_downloads: number
    total_storage_used: number
    media_server_count: number
    total_media_items: number
    // 系统
    image_cache_count: number
    image_cache_size: number
    // 其他
    recent_watch_history: ViewingHistory[]
    recent_media_backdrops: MediaBackdropItem[]
    recent_activities: TaskExecutionSummary[]
}

export interface DashboardActivityResponse {
    recent_activities: TaskExecutionSummary[]
}

export interface DashboardBackdropsResponse {
    recent_media_backdrops: MediaBackdropItem[]
}

export interface DashboardWatchHistoryResponse {
    watch_history: ViewingHistory[]
}

export function getDashboardStats() {
    return request.get<DashboardStatsResponse>('/dashboard/stats')
}

export function getDashboardBackdrops() {
    return request.get<DashboardBackdropsResponse>('/dashboard/backdrops')
}

export function getDashboardWatchHistory() {
    return request.get<DashboardWatchHistoryResponse>('/dashboard/watch-history')
}

export function getDashboardActivity() {
    return request.get<DashboardActivityResponse>('/dashboard/activity')
}
