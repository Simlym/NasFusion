/**
 * 错误处理工具
 */

import { AxiosError } from 'axios'

// 错误代码枚举
export enum ErrorCode {
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  FORBIDDEN_ERROR = 'FORBIDDEN_ERROR',
  NOT_FOUND_ERROR = 'NOT_FOUND_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

// 应用错误接口
export interface AppError {
  code: ErrorCode
  message: string
  statusCode?: number
  details?: Record<string, unknown>
  originalError?: Error | AxiosError
}

// 错误结果接口
export interface ErrorResult<T = unknown> {
  success: false
  error: AppError
  data?: T
}

// 成功结果接口
export interface SuccessResult<T = unknown> {
  success: true
  data: T
  error?: undefined
}

// 操作结果类型
export type Result<T = unknown> = SuccessResult<T> | ErrorResult<T>

/**
 * 从 Axios 错误解析应用错误
 */
export function parseAxiosError(error: AxiosError): AppError {
  // 网络错误（无响应）
  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return {
        code: ErrorCode.TIMEOUT_ERROR,
        message: '请求超时，请检查网络连接',
        originalError: error
      }
    }
    return {
      code: ErrorCode.NETWORK_ERROR,
      message: '网络错误，请检查网络连接',
      originalError: error
    }
  }

  const { status, data } = error.response

  // 根据状态码处理
  switch (status) {
    case 400:
      return {
        code: ErrorCode.VALIDATION_ERROR,
        message: (data as { detail?: string })?.detail || '请求参数错误',
        statusCode: status,
        details: data as Record<string, unknown>,
        originalError: error
      }
    case 401:
      return {
        code: ErrorCode.AUTH_ERROR,
        message: '未授权，请重新登录',
        statusCode: status,
        originalError: error
      }
    case 403:
      return {
        code: ErrorCode.FORBIDDEN_ERROR,
        message: '拒绝访问，权限不足',
        statusCode: status,
        originalError: error
      }
    case 404:
      return {
        code: ErrorCode.NOT_FOUND_ERROR,
        message: '请求的资源不存在',
        statusCode: status,
        originalError: error
      }
    case 422:
      return {
        code: ErrorCode.VALIDATION_ERROR,
        message: (data as { detail?: string })?.detail || '数据验证失败',
        statusCode: status,
        details: data as Record<string, unknown>,
        originalError: error
      }
    case 500:
    case 502:
    case 503:
    case 504:
      return {
        code: ErrorCode.SERVER_ERROR,
        message: '服务器错误，请稍后重试',
        statusCode: status,
        originalError: error
      }
    default:
      return {
        code: ErrorCode.UNKNOWN_ERROR,
        message: (data as { detail?: string })?.detail || `请求失败 (${status})`,
        statusCode: status,
        details: data as Record<string, unknown>,
        originalError: error
      }
  }
}

/**
 * 从任意错误解析应用错误
 */
export function parseError(error: unknown): AppError {
  if (error instanceof AxiosError) {
    return parseAxiosError(error)
  }

  if (error instanceof Error) {
    return {
      code: ErrorCode.UNKNOWN_ERROR,
      message: error.message || '未知错误',
      originalError: error
    }
  }

  return {
    code: ErrorCode.UNKNOWN_ERROR,
    message: String(error) || '未知错误'
  }
}

/**
 * 创建成功结果
 */
export function success<T>(data: T): SuccessResult<T> {
  return {
    success: true,
    data
  }
}

/**
 * 创建失败结果
 */
export function failure(error: AppError): ErrorResult {
  return {
    success: false,
    error
  }
}

/**
 * 包装异步操作，统一错误处理
 */
export async function tryCatch<T>(
  fn: () => Promise<T>,
  errorHandler?: (error: AppError) => void
): Promise<Result<T>> {
  try {
    const data = await fn()
    return success(data)
  } catch (error) {
    const appError = parseError(error)
    if (errorHandler) {
      errorHandler(appError)
    }
    return failure(appError)
  }
}

/**
 * 获取用户友好的错误消息
 */
export function getErrorMessage(error: AppError): string {
  return error.message
}

/**
 * 检查是否为认证错误
 */
export function isAuthError(error: AppError): boolean {
  return error.code === ErrorCode.AUTH_ERROR
}

/**
 * 检查是否为网络错误
 */
export function isNetworkError(error: AppError): boolean {
  return error.code === ErrorCode.NETWORK_ERROR || error.code === ErrorCode.TIMEOUT_ERROR
}
