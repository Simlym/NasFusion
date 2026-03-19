/**
 * 命名规范转换工具
 * 用于在前端 camelCase 和后端 snake_case 之间转换
 */

/**
 * 将 snake_case 字符串转换为 camelCase
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
}

/**
 * 将 camelCase 字符串转换为 snake_case
 */
export function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
}

/**
 * 递归将对象的所有键从 snake_case 转换为 camelCase
 */
export function keysToCamel<T>(obj: unknown): T {
  if (obj === null || obj === undefined) {
    return obj as T
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => keysToCamel(item)) as T
  }

  if (typeof obj === 'object' && obj !== null) {
    const result: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(obj)) {
      const camelKey = snakeToCamel(key)
      result[camelKey] = keysToCamel(value)
    }
    return result as T
  }

  return obj as T
}

/**
 * 递归将对象的所有键从 camelCase 转换为 snake_case
 */
export function keysToSnake<T>(obj: unknown): T {
  if (obj === null || obj === undefined) {
    return obj as T
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => keysToSnake(item)) as T
  }

  if (typeof obj === 'object' && obj !== null) {
    const result: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(obj)) {
      const snakeKey = camelToSnake(key)
      result[snakeKey] = keysToSnake(value)
    }
    return result as T
  }

  return obj as T
}

/**
 * 转换分页响应
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export function convertPaginatedResponse<T>(
  response: {
    items: unknown[]
    total: number
    page: number
    page_size: number
    total_pages: number
  },
  itemConverter?: (item: unknown) => T
): PaginatedResponse<T> {
  const converter = itemConverter || keysToCamel
  return {
    items: response.items.map((item) => converter(item) as T),
    total: response.total,
    page: response.page,
    pageSize: response.page_size,
    totalPages: response.total_pages
  }
}
