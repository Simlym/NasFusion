/**
 * 搜索组合函数
 */

import { ref, watch, computed } from 'vue'
import { useDebounceFn } from '@vueuse/core'

export interface SearchOptions {
  debounceTime?: number
  minLength?: number
  trimInput?: boolean
}

export function useSearch<T = string>(options: SearchOptions = {}) {
  const { debounceTime = 300, minLength = 0, trimInput = true } = options

  // 状态
  const searchText = ref('')
  const searchQuery = ref('')
  const isSearching = ref(false)
  const searchHistory = ref<string[]>([])

  // 计算属性
  const normalizedQuery = computed(() => {
    const query = trimInput ? searchQuery.value.trim() : searchQuery.value
    return query
  })

  const isValidSearch = computed(() => normalizedQuery.value.length >= minLength)

  const hasSearchText = computed(() => searchText.value.length > 0)

  // 防抖更新搜索查询
  const debouncedUpdate = useDebounceFn(() => {
    const query = trimInput ? searchText.value.trim() : searchText.value
    if (query.length >= minLength) {
      searchQuery.value = query
      // 添加到历史记录
      if (query && !searchHistory.value.includes(query)) {
        searchHistory.value.unshift(query)
        // 只保留最近10条
        if (searchHistory.value.length > 10) {
          searchHistory.value.pop()
        }
      }
    } else {
      searchQuery.value = ''
    }
    isSearching.value = false
  }, debounceTime)

  // 监听搜索文本变化
  watch(searchText, () => {
    isSearching.value = true
    debouncedUpdate()
  })

  // 方法
  function setSearchText(text: string) {
    searchText.value = text
  }

  function clearSearch() {
    searchText.value = ''
    searchQuery.value = ''
    isSearching.value = false
  }

  function clearHistory() {
    searchHistory.value = []
  }

  function removeFromHistory(query: string) {
    const index = searchHistory.value.indexOf(query)
    if (index !== -1) {
      searchHistory.value.splice(index, 1)
    }
  }

  function searchFromHistory(query: string) {
    searchText.value = query
  }

  // 获取搜索参数（用于 API 请求）
  function getParams() {
    return {
      search: normalizedQuery.value || undefined
    }
  }

  return {
    // 状态
    searchText,
    searchQuery,
    isSearching,
    searchHistory,

    // 计算属性
    normalizedQuery,
    isValidSearch,
    hasSearchText,

    // 方法
    setSearchText,
    clearSearch,
    clearHistory,
    removeFromHistory,
    searchFromHistory,
    getParams
  }
}
