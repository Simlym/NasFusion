/**
 * 页面级标签栏管理 Composable
 *
 * 统一管理页面级标签栏的显示、切换和状态同步
 */

import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { PageTabsConfig } from '@/router'
import { useSettingsStore } from '@/stores'

export function usePageTabs() {
  const route = useRoute()
  const router = useRouter()
  const settingsStore = useSettingsStore()

  // 当前路由的标签栏配置
  const currentTabsConfig = computed<PageTabsConfig | undefined>(() => {
    return route.meta?.pageTabs
  })

  // 是否显示标签栏
  const showTabs = computed(() => {
    return currentTabsConfig.value?.enabled === true
  })

  // 标签栏样式（card/pill/underline）
  const tabStyle = computed(() => {
    return currentTabsConfig.value?.style || 'card'
  })

  // 标签列表
  const tabs = computed(() => {
    const staticTabs = currentTabsConfig.value?.tabs || []

    // 只在媒体库页面动态添加限制级页签（从全局 store 读取）
    if (route.name === 'MediaLibrary' && settingsStore.showAdultContent) {
      return [
        ...staticTabs,
        { name: 'adult', label: '18+', icon: 'lucide:eye-off' }
      ]
    }

    return staticTabs
  })

  // 当前激活的标签
  const activeTab = ref<string>('')

  // 初始化激活标签
  const initActiveTab = () => {
    const queryTab = route.query.tab as string
    const defaultTab = currentTabsConfig.value?.defaultTab
    const firstTab = tabs.value[0]?.name

    if (queryTab && tabs.value.some(tab => tab.name === queryTab)) {
      // 如果 URL 中有有效的 tab 参数，使用它
      activeTab.value = queryTab
    } else if (defaultTab) {
      // 否则使用默认标签
      activeTab.value = defaultTab
      // 更新 URL（不触发导航）
      if (showTabs.value) {
        router.replace({
          query: { ...route.query, tab: defaultTab }
        })
      }
    } else if (firstTab) {
      // 否则使用第一个标签
      activeTab.value = firstTab
      if (showTabs.value) {
        router.replace({
          query: { ...route.query, tab: firstTab }
        })
      }
    }
  }

  // 监听路由变化，同步激活标签
  watch(
    () => route.query.tab,
    (newTab) => {
      if (newTab && typeof newTab === 'string' && tabs.value.some(tab => tab.name === newTab)) {
        activeTab.value = newTab
      }
    }
  )

  // 监听路由路径变化，重新初始化
  watch(
    () => route.path,
    () => {
      initActiveTab()
    },
    { immediate: true }
  )

  // 切换标签
  const changeTab = (tabName: string) => {
    if (!tabs.value.some(tab => tab.name === tabName)) {
      console.warn(`[usePageTabs] Tab "${tabName}" not found in config`)
      return
    }

    // 更新 URL
    router.push({
      path: route.path,
      query: { ...route.query, tab: tabName }
    })
  }

  return {
    // 状态
    showTabs,
    tabStyle,
    tabs,
    activeTab,
    currentTabsConfig,

    // 方法
    changeTab
  }
}
