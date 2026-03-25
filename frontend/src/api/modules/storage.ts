/**
 * 存储挂载点相关 API
 */

import request from '../request'

// ==================== 类型定义 ====================

export interface StorageMountCreate {
    name: string
    mount_type: 'download' | 'library'
    container_path: string
    host_path?: string
    media_category?: string
    is_default?: boolean
    priority?: number
}

export interface StorageMount {
    id: number
    name: string
    mount_type: 'download' | 'library'
    container_path: string
    host_path?: string
    device_id?: number
    disk_group?: string
    media_category?: string
    priority: number
    is_default: boolean
    is_enabled: boolean
    is_accessible: boolean
    total_space?: number
    used_space?: number
    free_space?: number
    usage_percent?: number
    custom_label?: string
    description?: string
    last_scan_at?: string
    created_at: string
    updated_at: string
    is_same_disk?: boolean
}

export interface StorageMountUpdate {
    name?: string
    container_path?: string
    host_path?: string
    media_category?: string
    priority?: number
    is_default?: boolean
    is_enabled?: boolean
    custom_label?: string
    description?: string
    disk_group?: string
}

export interface StorageMountListResponse {
    total: number
    items: StorageMount[]
}

export interface DownloadMountRecommendation {
    mounts: StorageMount[]
    target_library_mount?: StorageMount
}

export interface SameDiskCheckRequest {
    path1: string
    path2: string
}

export interface SameDiskCheckResponse {
    same_disk: boolean
    can_hardlink: boolean
    device_id_1?: number
    device_id_2?: number
    reason?: string
}

export interface ScanMountsResponse {
    count: number
    message: string
}

export interface RefreshDiskInfoRequest {
    mount_id?: number
}

export interface RefreshDiskInfoResponse {
    count: number
}

export interface StorageStatsResponse {
    total_mounts: number
    download_mounts: number
    library_mounts: number
    total_space: number
    used_space: number
    free_space: number
    accessible_mounts: number
    inaccessible_mounts: number
}

// ==================== API 函数 ====================

/**
 * 获取存储挂载点列表
 */
export function getStorageMounts(params?: {
    mount_type?: string
    media_category?: string
    is_enabled?: boolean
}) {
    return request.get<StorageMountListResponse>('/storage-mounts', { params })
}

/**
 * 创建存储挂载点
 */
export function createStorageMount(data: StorageMountCreate) {
    return request.post<StorageMount>('/storage-mounts', data)
}

/**
 * 删除存储挂载点
 */
export function deleteStorageMount(mountId: number) {
    return request.delete(`/storage-mounts/${mountId}`)
}

/**
 * 获取指定挂载点详情
 */
export function getStorageMount(mountId: number) {
    return request.get<StorageMount>(`/storage-mounts/${mountId}`)
}

/**
 * 更新挂载点配置
 */
export function updateStorageMount(mountId: number, data: StorageMountUpdate) {
    return request.patch<StorageMount>(`/storage-mounts/${mountId}`, data)
}

/**
 * 获取推荐的下载挂载点
 */
export function getDownloadMountsForMedia(params: {
    media_category: string
    target_library_mount_id?: number
}) {
    return request.get<DownloadMountRecommendation>('/storage-mounts/download-mounts', { params })
}

/**
 * 获取指定分类的媒体库挂载点
 */
export function getLibraryMountsByCategory(mediaCategory: string) {
    return request.get<{ mounts: StorageMount[] }>('/storage-mounts/library-mounts', {
        params: { media_category: mediaCategory }
    })
}

/**
 * 获取存储统计信息
 */
export function getStorageStats() {
    return request.get<StorageStatsResponse>('/storage-mounts/stats')
}

/**
 * 扫描并初始化存储挂载点
 */
export function scanStorageMounts() {
    return request.post<ScanMountsResponse>('/storage-mounts/scan')
}

/**
 * 刷新挂载点磁盘空间信息
 */
export function refreshDiskInfo(mountId?: number) {
    return request.post<RefreshDiskInfoResponse>('/storage-mounts/refresh-disk-info', {
        mount_id: mountId
    })
}

/**
 * 检查两个路径是否在同一磁盘
 */
export function checkSameDisk(path1: string, path2: string) {
    return request.post<SameDiskCheckResponse>('/storage-mounts/check-same-disk', {
        path1,
        path2
    })
}

// ==================== 工具函数 ====================

/**
 * 格式化文件大小
 */
export function formatSize(bytes?: number): string {
    if (!bytes) return '-'
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
}

/**
 * 获取空间使用率颜色
 */
export function getSpaceColor(ratio: number): string {
    if (ratio < 0.6) return '#67C23A' // 绿色
    if (ratio < 0.8) return '#E6A23C' // 橙色
    return '#F56C6C' // 红色
}

/**
 * 媒体分类标签映射
 */
export const MEDIA_CATEGORY_LABELS: Record<string, string> = {
    movie: '电影',
    tv: '电视剧',
    music: '音乐',
    book: '书籍',
    anime: '动漫',
    adult: '成人',
    game: '游戏',
    other: '其他'
}

/**
 * 获取媒体分类标签
 */
export function getMediaCategoryLabel(category?: string): string {
    return category ? MEDIA_CATEGORY_LABELS[category] || category : '-'
}
