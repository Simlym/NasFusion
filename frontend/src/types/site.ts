/**
 * PT站点相关类型定义
 */

// PT站点类型
export enum SiteType {
  MTEAM = 'mteam',
  CHDBITS = 'chdbits',
  HDCHINA = 'hdchina',
  NEXUSPHP = 'nexusphp',
  GAZELLE = 'gazelle',
  UNIT3D = 'unit3d',
  OTHER = 'other'
}

// PT站点认证类型
export enum AuthType {
  COOKIE = 'cookie',
  PASSKEY = 'passkey',
  USER_PASS = 'user_pass'
}

// 同步模式
export enum SyncMode {
  TIME_BASED = 'time_based',
  PAGE_BASED = 'page_based',
  ID_BASED = 'id_based'
}

// PT站点状态
export enum SiteStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  DISABLED = 'disabled'
}

// PT站点健康状态
export enum HealthStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  ERROR = 'error',
  UNKNOWN = 'unknown'
}

// PT站点配置
export interface PTSite {
  id: number
  name: string
  type: string
  domain: string
  base_url: string
  auth_type: AuthType
  // 认证信息已设置标志（不返回实际值）
  has_auth_cookie?: boolean
  has_auth_passkey?: boolean
  has_auth_password?: boolean
  proxy_config?: Record<string, any>
  capabilities?: Record<string, any>
  sync_enabled: boolean
  sync_strategy?: SyncMode
  sync_interval?: number
  sync_config?: Record<string, any>
  last_sync_at?: string
  last_sync_status?: string
  last_sync_error?: string
  request_interval?: number
  max_requests_per_day?: number
  daily_requests_used: number
  status: 'active' | 'inactive' | 'error'
  health_check_at?: string
  health_status?: 'healthy' | 'unhealthy'
  total_resources: number
  total_synced: number
  created_at: string
  updated_at: string
}

// PT站点表单
export interface PTSiteForm {
  name: string
  type: string
  domain: string
  base_url: string
  auth_type: AuthType
  auth_cookie?: string
  auth_passkey?: string
  auth_username?: string
  auth_password?: string
  proxy_config?: Record<string, any>
  capabilities?: Record<string, any>
  sync_enabled: boolean
  sync_strategy?: SyncMode
  sync_interval?: number
  sync_config?: Record<string, any>
  request_interval?: number
  max_requests_per_day?: number
}

// PT站点统计
export interface PTSiteStats {
  siteId: number
  siteName: string
  totalResources: number
  todayAdded: number
  syncStatus: string
  lastSyncTime?: string
  healthStatus: string
}
