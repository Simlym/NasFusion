/**
 * Axios 请求配置
 */

import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { parseAxiosError, ErrorCode } from '@/utils/error'

// Token 相关常量
const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const TOKEN_EXPIRES_KEY = 'token_expires_at'

// 是否正在刷新 token
let isRefreshing = false
// 等待刷新 token 的请求队列
let refreshSubscribers: Array<(token: string) => void> = []

/**
 * 获取存储的 token
 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 设置 token
 */
export function setToken(token: string, expiresIn?: number): void {
  localStorage.setItem(TOKEN_KEY, token)
  if (expiresIn) {
    const expiresAt = Date.now() + expiresIn * 1000
    localStorage.setItem(TOKEN_EXPIRES_KEY, String(expiresAt))
  }
}

/**
 * 设置刷新 token
 */
export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

/**
 * 获取刷新 token
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

/**
 * 清除所有 token
 */
export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(TOKEN_EXPIRES_KEY)
}

/**
 * 检查 token 是否即将过期（5分钟内）
 */
export function isTokenExpiringSoon(): boolean {
  const expiresAt = localStorage.getItem(TOKEN_EXPIRES_KEY)
  if (!expiresAt) return false

  const expiresTime = parseInt(expiresAt, 10)
  const fiveMinutes = 5 * 60 * 1000
  return Date.now() + fiveMinutes > expiresTime
}

/**
 * 订阅 token 刷新
 */
function subscribeTokenRefresh(callback: (token: string) => void): void {
  refreshSubscribers.push(callback)
}

/**
 * 通知所有订阅者 token 已刷新
 */
function onTokenRefreshed(token: string): void {
  refreshSubscribers.forEach((callback) => callback(token))
  refreshSubscribers = []
}

// 创建 axios 实例
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  paramsSerializer: {
    indexes: null // 数组参数序列化为 key=val1&key=val2 格式，不带 []
  }
})

// 请求拦截器
request.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // 从本地存储获取 token
    const token = getToken()

    if (token) {
      // 检查 token 是否即将过期（提前 5 分钟刷新）
      if (isTokenExpiringSoon() && !config.url?.includes('/auth/refresh')) {
        const refreshToken = getRefreshToken()

        if (refreshToken && !isRefreshing) {
          isRefreshing = true

          try {
            // 主动刷新 token
            const response = await axios.post(
              `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/auth/refresh`,
              { refresh_token: refreshToken }
            )

            const newToken = response.data.access_token
            setToken(newToken, response.data.expires_in)

            if (response.data.refresh_token) {
              setRefreshToken(response.data.refresh_token)
            }

            isRefreshing = false
            onTokenRefreshed(newToken)

            // 使用新 token
            if (config.headers) {
              config.headers.Authorization = `Bearer ${newToken}`
            }
          } catch (error) {
            isRefreshing = false
            // 刷新失败，使用原 token（让后端返回 401 后再处理）
            if (config.headers) {
              config.headers.Authorization = `Bearer ${token}`
            }
          }
        } else if (config.headers) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } else if (config.headers) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }

    return config
  },
  (error: AxiosError) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    // FastAPI 返回的数据结构通常是直接的 JSON 对象
    return response
  },
  async (error: AxiosError) => {
    const appError = parseAxiosError(error)

    // 根据错误类型处理
    switch (appError.code) {
      case ErrorCode.AUTH_ERROR:
        // 登录接口的认证错误由调用方处理，不做重定向
        if (error.config?.url?.includes('/auth/login')) {
          break
        }
        // 尝试刷新 token
        if (error.config && !error.config.url?.includes('/auth/refresh')) {
          const refreshToken = getRefreshToken()

          if (refreshToken && !isRefreshing) {
            isRefreshing = true

            try {
              // 尝试刷新 token
              const response = await axios.post(
                `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/auth/refresh`,
                { refresh_token: refreshToken }
              )

              const newToken = response.data.access_token
              setToken(newToken, response.data.expires_in)

              if (response.data.refresh_token) {
                setRefreshToken(response.data.refresh_token)
              }

              isRefreshing = false
              onTokenRefreshed(newToken)

              // 重试原请求
              if (error.config) {
                error.config.headers.Authorization = `Bearer ${newToken}`
                return request(error.config)
              }
            } catch (refreshError) {
              isRefreshing = false
              clearTokens()
              ElMessage.error('登录已过期，请重新登录')
              window.location.href = '/login'
              return Promise.reject(refreshError)
            }
          } else if (isRefreshing) {
            // 等待 token 刷新完成
            return new Promise((resolve) => {
              subscribeTokenRefresh((token: string) => {
                if (error.config) {
                  error.config.headers.Authorization = `Bearer ${token}`
                  resolve(request(error.config))
                }
              })
            })
          } else {
            // 没有刷新 token，直接登出
            clearTokens()
            ElMessage.error('未授权，请重新登录')
            window.location.href = '/login'
          }
        }
        break

      case ErrorCode.FORBIDDEN_ERROR:
        // 登录接口的 403 由调用方处理（账户锁定/禁用）
        if (!error.config?.url?.includes('/auth/login')) {
          ElMessage.error(appError.message)
        }
        break

      case ErrorCode.NOT_FOUND_ERROR:
        // 对于以下情况，404 是正常/可接受的，静默处理不显示错误：
        // 1. system-settings 的 GET 请求（设置不存在）
        // 2. media-servers 的 /latest、/sessions 等非关键数据获取请求
        const url = error.config?.url || ''
        const isSilent404 =
          (url.includes('/system-settings/') && error.config?.method === 'get') ||
          (url.includes('/media-servers/') && (url.includes('/latest') || url.includes('/sessions')))

        if (!isSilent404) {
          ElMessage.error(appError.message)
        }
        break

      case ErrorCode.VALIDATION_ERROR:
        ElMessage.error(appError.message)
        break

      case ErrorCode.SERVER_ERROR:
        ElMessage.error(appError.message)
        break

      case ErrorCode.NETWORK_ERROR:
      case ErrorCode.TIMEOUT_ERROR:
        ElMessage.error(appError.message)
        break

      default:
        ElMessage.error(appError.message)
    }

    return Promise.reject(error)
  }
)

export default request
