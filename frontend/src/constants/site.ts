/**
 * PT站点相关常量定义
 * 与后端 backend/app/constants/pt_site.py 保持一致
 */

/**
 * 站点框架（schema）— 决定使用哪个适配器解析站点。
 * 这是「手动配置」时真正要选的东西：选的是解析协议/框架，而非某个具体站点。
 * 具体站点（天空 / 彩虹岛 / 铂金家…）请走「快速添加」从预设创建。
 * 与后端 backend/app/constants/site_presets.py 的 SITE_SCHEMA_* 保持一致。
 */
export const SITE_SCHEMA_NEXUSPHP = 'nexusphp'
export const SITE_SCHEMA_MTEAM = 'mteam'
export const SITE_SCHEMA_UNIT3D = 'unit3d'
export const SITE_SCHEMA_GAZELLE = 'gazelle'
export const SITE_SCHEMA_GENERIC_JSON_API = 'generic_json_api'

// 框架显示名称映射
export const SITE_SCHEMA_LABELS: Record<string, string> = {
  [SITE_SCHEMA_NEXUSPHP]: 'NexusPHP（网页解析）',
  [SITE_SCHEMA_MTEAM]: '馒头 / M-Team（API）',
  [SITE_SCHEMA_UNIT3D]: 'Unit3D（国际站，网页解析）',
  [SITE_SCHEMA_GENERIC_JSON_API]: '通用 JSON API'
  // 注：gazelle 暂无对应适配器（后端未注册），故不在手动配置下拉中提供
}

// 框架选项（用于「手动配置」站点类型下拉框）
// 仅列出后端 SCHEMA_REGISTRY 已注册、可正常工作的框架。
export const SITE_SCHEMA_OPTIONS = [
  SITE_SCHEMA_NEXUSPHP,
  SITE_SCHEMA_MTEAM,
  SITE_SCHEMA_UNIT3D,
  SITE_SCHEMA_GENERIC_JSON_API
].map((value) => ({
  label: SITE_SCHEMA_LABELS[value],
  value
}))

// 兼容别名：旧代码引用 SITE_TYPE_OPTIONS 的地方继续可用（现指向框架选项）
export const SITE_TYPE_OPTIONS = SITE_SCHEMA_OPTIONS

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
