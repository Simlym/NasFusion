/**
 * 应用全局状态管理
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 侧边栏是否折叠
  const sidebarCollapsed = ref(false)

  // 主题模式
  const theme = ref<'light' | 'dark' | 'auto'>('auto')

  // 语言
  const language = ref<string>('zh-CN')

  // 加载状态
  const loading = ref(false)

  // 切换侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // 设置主题
  function setTheme(newTheme: 'light' | 'dark' | 'auto') {
    theme.value = newTheme
    // 可以在这里处理主题切换逻辑
  }

  // 设置语言
  function setLanguage(lang: string) {
    language.value = lang
  }

  // 设置加载状态
  function setLoading(status: boolean) {
    loading.value = status
  }

  return {
    sidebarCollapsed,
    theme,
    language,
    loading,
    toggleSidebar,
    setTheme,
    setLanguage,
    setLoading
  }
})
