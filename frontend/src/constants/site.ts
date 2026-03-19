/**
 * PT站点相关常量定义
 * 与后端 backend/app/constants/pt_site.py 保持一致
 */

// 站点类型常量
export const SITE_TYPE_MTEAM = 'mteam'
export const SITE_TYPE_NEXUSPHP = 'nexusphp'
export const SITE_TYPE_HDSKY = 'hdsky'
export const SITE_TYPE_CHDBITS = 'chdbits'
export const SITE_TYPE_PTHOME = 'pthome'
export const SITE_TYPE_OURBITS = 'ourbits'
export const SITE_TYPE_HDCHINA = 'hdchina'
export const SITE_TYPE_GAZELLE = 'gazelle'
export const SITE_TYPE_UNIT3D = 'unit3d'
export const SITE_TYPE_OTHER = 'other'

// 站点类型列表
export const SITE_TYPES = [
  SITE_TYPE_MTEAM,
  SITE_TYPE_NEXUSPHP,
  SITE_TYPE_HDSKY,
  SITE_TYPE_CHDBITS,
  SITE_TYPE_PTHOME,
  SITE_TYPE_OURBITS,
  SITE_TYPE_HDCHINA,
  SITE_TYPE_GAZELLE,
  SITE_TYPE_UNIT3D,
  SITE_TYPE_OTHER
] as const

// 站点类型显示名称映射
export const SITE_TYPE_LABELS: Record<string, string> = {
  [SITE_TYPE_MTEAM]: '馒头 (API)',
  [SITE_TYPE_NEXUSPHP]: 'NexusPHP通用',
  [SITE_TYPE_HDSKY]: '天空',
  [SITE_TYPE_CHDBITS]: '彩虹岛',
  [SITE_TYPE_PTHOME]: '铂金家',
  [SITE_TYPE_OURBITS]: '我堡',
  [SITE_TYPE_HDCHINA]: '瓷器',
  [SITE_TYPE_GAZELLE]: 'Gazelle',
  [SITE_TYPE_UNIT3D]: 'Unit3D',
  [SITE_TYPE_OTHER]: '其他'
}

// 站点类型选项（用于下拉框）
export const SITE_TYPE_OPTIONS = SITE_TYPES.map((value) => ({
  label: SITE_TYPE_LABELS[value],
  value
}))

// 站点状态常量
export const SITE_STATUS_ACTIVE = 'active'
export const SITE_STATUS_INACTIVE = 'inactive'
export const SITE_STATUS_DISABLED = 'disabled'

export const SITE_STATUSES = [
  SITE_STATUS_ACTIVE,
  SITE_STATUS_INACTIVE,
  SITE_STATUS_DISABLED
] as const

// 站点状态显示名称映射
export const SITE_STATUS_LABELS: Record<string, string> = {
  [SITE_STATUS_ACTIVE]: '启用',
  [SITE_STATUS_INACTIVE]: '未启用',
  [SITE_STATUS_DISABLED]: '禁用'
}

// 站点健康状态常量
export const HEALTH_STATUS_HEALTHY = 'healthy'
export const HEALTH_STATUS_WARNING = 'warning'
export const HEALTH_STATUS_ERROR = 'error'
export const HEALTH_STATUS_UNKNOWN = 'unknown'

export const HEALTH_STATUSES = [
  HEALTH_STATUS_HEALTHY,
  HEALTH_STATUS_WARNING,
  HEALTH_STATUS_ERROR,
  HEALTH_STATUS_UNKNOWN
] as const

// 站点健康状态显示名称映射
export const HEALTH_STATUS_LABELS: Record<string, string> = {
  [HEALTH_STATUS_HEALTHY]: '健康',
  [HEALTH_STATUS_WARNING]: '警告',
  [HEALTH_STATUS_ERROR]: '错误',
  [HEALTH_STATUS_UNKNOWN]: '未知'
}

// 认证类型常量
export const AUTH_TYPE_COOKIE = 'cookie'
export const AUTH_TYPE_PASSKEY = 'passkey'
export const AUTH_TYPE_USER_PASS = 'user_pass'

export const AUTH_TYPES = [AUTH_TYPE_COOKIE, AUTH_TYPE_PASSKEY, AUTH_TYPE_USER_PASS] as const

// 认证类型显示名称映射
export const AUTH_TYPE_LABELS: Record<string, string> = {
  [AUTH_TYPE_COOKIE]: 'Cookie',
  [AUTH_TYPE_PASSKEY]: 'Passkey',
  [AUTH_TYPE_USER_PASS]: '用户名密码'
}

// 认证类型选项（用于下拉框）
export const AUTH_TYPE_OPTIONS = AUTH_TYPES.map((value) => ({
  label: AUTH_TYPE_LABELS[value],
  value
}))
