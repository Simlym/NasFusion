/**
 * 环境变量工具函数
 */

// 获取环境变量
export const getEnv = (key: string): string => {
  return import.meta.env[key] || ''
}

// 获取API基础URL
export const getApiBaseUrl = (): string => {
  return import.meta.env.VITE_API_BASE_URL || '/api'
}

// 获取应用标题
export const getAppTitle = (): string => {
  return import.meta.env.VITE_APP_TITLE || 'NasFusion'
}

// 获取应用版本
export const getAppVersion = (): string => {
  return import.meta.env.VITE_APP_VERSION || '0.1.0'
}

// 是否为开发环境
export const isDevelopment = (): boolean => {
  return import.meta.env.MODE === 'development'
}

// 是否为生产环境
export const isProduction = (): boolean => {
  return import.meta.env.MODE === 'production'
}

// 是否显示调试信息
export const showDebug = (): boolean => {
  return import.meta.env.VITE_SHOW_DEBUG === 'true'
}
