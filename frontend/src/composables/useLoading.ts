/**
 * 加载状态组合函数
 */

import { ref, computed } from 'vue'

export interface LoadingOptions {
  initialLoading?: boolean
  minLoadingTime?: number
}

export function useLoading(options: LoadingOptions = {}) {
  const { initialLoading = false, minLoadingTime = 0 } = options

  // 状态
  const loading = ref(initialLoading)
  const loadingCount = ref(0)
  const error = ref<Error | null>(null)
  const lastLoadTime = ref<number>(0)

  // 计算属性
  const isLoading = computed(() => loading.value || loadingCount.value > 0)
  const hasError = computed(() => error.value !== null)

  // 开始加载
  function startLoading() {
    loading.value = true
    loadingCount.value++
    lastLoadTime.value = Date.now()
    error.value = null
  }

  // 停止加载（考虑最小加载时间）
  async function stopLoading() {
    loadingCount.value = Math.max(0, loadingCount.value - 1)

    if (minLoadingTime > 0 && loadingCount.value === 0) {
      const elapsed = Date.now() - lastLoadTime.value
      if (elapsed < minLoadingTime) {
        await new Promise((resolve) => setTimeout(resolve, minLoadingTime - elapsed))
      }
    }

    if (loadingCount.value === 0) {
      loading.value = false
    }
  }

  // 设置错误
  function setError(err: Error | string | null) {
    if (err === null) {
      error.value = null
    } else if (typeof err === 'string') {
      error.value = new Error(err)
    } else {
      error.value = err
    }
  }

  // 清除错误
  function clearError() {
    error.value = null
  }

  // 重置状态
  function reset() {
    loading.value = false
    loadingCount.value = 0
    error.value = null
    lastLoadTime.value = 0
  }

  // 包装异步函数
  async function withLoading<T>(fn: () => Promise<T>): Promise<T> {
    startLoading()
    try {
      const result = await fn()
      await stopLoading()
      return result
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
      await stopLoading()
      throw err
    }
  }

  return {
    // 状态
    loading,
    error,

    // 计算属性
    isLoading,
    hasError,

    // 方法
    startLoading,
    stopLoading,
    setError,
    clearError,
    reset,
    withLoading
  }
}
