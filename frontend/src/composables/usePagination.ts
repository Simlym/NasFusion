/**
 * 分页组合函数
 */

import { ref, computed, watch } from 'vue'

export interface PaginationOptions {
  defaultPage?: number
  defaultPageSize?: number
  pageSizes?: number[]
}

export interface PaginationState {
  page: number
  pageSize: number
  total: number
}

export function usePagination(options: PaginationOptions = {}) {
  const { defaultPage = 1, defaultPageSize = 20, pageSizes = [10, 20, 50, 100] } = options

  // 状态
  const currentPage = ref(defaultPage)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)

  // 计算属性
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
  const hasNextPage = computed(() => currentPage.value < totalPages.value)
  const hasPrevPage = computed(() => currentPage.value > 1)
  const offset = computed(() => (currentPage.value - 1) * pageSize.value)

  // 分页信息
  const paginationInfo = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value + 1
    const end = Math.min(currentPage.value * pageSize.value, total.value)
    return {
      start,
      end,
      total: total.value,
      text: `显示 ${start}-${end} 条，共 ${total.value} 条`
    }
  })

  // 方法
  function setPage(page: number) {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page
    }
  }

  function setPageSize(size: number) {
    pageSize.value = size
    // 重置到第一页
    currentPage.value = 1
  }

  function setTotal(value: number) {
    total.value = value
    // 如果当前页超出范围，调整到最后一页
    if (currentPage.value > totalPages.value && totalPages.value > 0) {
      currentPage.value = totalPages.value
    }
  }

  function nextPage() {
    if (hasNextPage.value) {
      currentPage.value++
    }
  }

  function prevPage() {
    if (hasPrevPage.value) {
      currentPage.value--
    }
  }

  function reset() {
    currentPage.value = defaultPage
    pageSize.value = defaultPageSize
    total.value = 0
  }

  // 获取分页参数（用于 API 请求）
  function getParams() {
    return {
      page: currentPage.value,
      page_size: pageSize.value
    }
  }

  return {
    // 状态
    currentPage,
    pageSize,
    total,
    pageSizes,

    // 计算属性
    totalPages,
    hasNextPage,
    hasPrevPage,
    offset,
    paginationInfo,

    // 方法
    setPage,
    setPageSize,
    setTotal,
    nextPage,
    prevPage,
    reset,
    getParams
  }
}
