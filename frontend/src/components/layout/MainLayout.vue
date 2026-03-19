<template>
  <el-container class="main-layout">
    <!-- Loading Bar -->
    <LoadingBar ref="loadingBarRef" />

    <!-- Mobile Overlay -->
    <div 
      v-if="!isCollapse && isMobile" 
      class="sidebar-overlay" 
      @click="isCollapse = true"
    ></div>

    <!-- Sidebar -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo">
        <h2 v-if="!isCollapse">NasFusion</h2>
        <h2 v-else class="logo-collapsed">N</h2>
      </div>

      <!-- 菜单 - 按分组显示 -->
      <div class="menu-container">
        <template v-for="group in menuGroups" :key="group.key">
          <!-- 分组标题 -->
          <div v-if="!isCollapse && getGroupRoutes(group.key).length > 0" class="menu-group-title">
            {{ group.label }}
          </div>

          <!-- 分组菜单项 -->
          <el-menu
            :default-active="activeMenu"
            class="sidebar-menu"
            router
            :collapse="isCollapse"
          >
            <el-menu-item
              v-for="route in getGroupRoutes(group.key)"
              :key="route.path"
              :index="route.path"
              class="menu-item-enhanced"
            >
              <AppIcon v-if="route.meta?.icon" :name="route.meta.icon" :size="18" />
              <template #title>{{ route.meta?.title }}</template>
            </el-menu-item>
          </el-menu>
        </template>
      </div>
    </el-aside>

    <!-- Main content area -->
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-left">
          <span class="collapse-icon" @click="toggleSidebar">
            <AppIcon name="lucide:menu" :size="20" />
          </span>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 刷新按钮 -->
          <el-button type="default" circle title="刷新" @click="handleRefresh">
            <AppIcon name="lucide:refresh-cw" :size="15" />
          </el-button>

          <!-- 通知中心 -->
          <el-badge :value="unreadCount" :hidden="unreadCount === 0">
            <el-button
              type="default"
              circle
              title="通知中心"
              @click="goToNotifications"
            >
              <AppIcon name="lucide:bell" :size="15" />
            </el-button>
          </el-badge>

          <!-- 主题切换下拉菜单 -->
          <el-dropdown @command="handleThemeChange">
            <el-button
              type="default"
              circle
              :title="'当前主题: ' + themeLabel"
            >
              <AppIcon :name="themeIconName" :size="15" />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="light" :class="{ 'is-active': currentTheme === 'light' }">
                  <AppIcon name="lucide:sun" :size="14" />
                  浅色
                </el-dropdown-item>
                <el-dropdown-item command="dark" :class="{ 'is-active': currentTheme === 'dark' }">
                  <AppIcon name="lucide:moon" :size="14" />
                  深色
                </el-dropdown-item>
                <el-dropdown-item command="ocean" :class="{ 'is-active': currentTheme === 'ocean' }">
                  <AppIcon name="lucide:waves" :size="14" />
                  海洋
                </el-dropdown-item>
                <el-dropdown-item command="warm" :class="{ 'is-active': currentTheme === 'warm' }">
                  <AppIcon name="lucide:sunrise" :size="14" />
                  暖光
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 用户头像下拉菜单 -->
          <el-dropdown @command="handleUserMenuCommand">
            <div class="user-avatar-wrapper">
              <el-avatar :size="36" :src="userAvatar">
                {{ userInitial }}
              </el-avatar>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled class="user-info-item">
                  <div class="user-info">
                    <div class="user-name">{{ userName }}</div>
                    <div class="user-email">{{ userEmail }}</div>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item divided command="profile">
                  <AppIcon name="lucide:user" :size="14" />
                  个人资料
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <AppIcon name="lucide:log-out" :size="14" />
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 页面级标签栏 -->
      <div v-if="showTabs" class="page-tabs-bar" :class="`page-tabs-${tabStyle}`">
        <el-tabs
          :model-value="activeTab"
          class="page-level-tabs"
          @tab-change="changeTab"
        >
          <el-tab-pane
            v-for="tab in tabs"
            :key="tab.name"
            :name="tab.name"
          >
            <template #label>
              <span class="tab-label">
                <AppIcon v-if="tab.icon" :name="tab.icon" :size="14" />
                <span>{{ tab.label }}</span>
              </span>
            </template>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Content -->
      <el-main class="main-content" :class="{ 'no-padding': route.name === 'Tasks' }">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <!-- 使用 keep-alive 缓存媒体库组件，保持滚动位置和数据状态 -->
            <keep-alive :include="['MediaLibrary']">
              <component :is="Component" :key="route.path" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- Mobile Bottom Navigation -->
    <MobileBottomNav />
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import AppIcon from '@/components/common/AppIcon.vue'
import { menuGroups } from '@/router/groups'
import LoadingBar from '@/components/common/LoadingBar.vue'
import MobileBottomNav from '@/components/layout/MobileBottomNav.vue'
import { usePageTabs } from '@/composables/usePageTabs'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 页面级标签栏
const { showTabs, tabStyle, tabs, activeTab, changeTab } = usePageTabs()

// Loading bar ref
const loadingBarRef = ref<InstanceType<typeof LoadingBar> | null>(null)

// Sidebar state
const isCollapse = ref(false)
const isMobile = ref(false)

const sidebarWidth = computed(() => {
  if (isMobile.value) {
    return isCollapse.value ? '0px' : '180px'
  }
  return isCollapse.value ? '64px' : '180px'
})

const checkMobile = () => {
  const mobile = window.innerWidth <= 768
  isMobile.value = mobile
  if (mobile) {
    isCollapse.value = true
  }
}

// 多主题支持
type ThemeType = 'light' | 'dark' | 'ocean' | 'warm'
const THEME_STORAGE_KEY = 'theme-color-mode'
const VALID_THEMES: ThemeType[] = ['light', 'dark', 'ocean', 'warm']

// 获取有效的主题值
const getValidTheme = (): ThemeType => {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  if (stored && VALID_THEMES.includes(stored as ThemeType)) {
    return stored as ThemeType
  }
  return 'ocean' // 默认海洋色
}

const currentTheme = ref<ThemeType>(getValidTheme())

// 主题配置
const themeConfig: Record<ThemeType, { icon: string; label: string }> = {
  light: { icon: 'lucide:sun', label: '浅色' },
  dark: { icon: 'lucide:moon', label: '深色' },
  ocean: { icon: 'lucide:waves', label: '海洋' },
  warm: { icon: 'lucide:sunrise', label: '暖光' }
}

const themeIconName = computed(() => themeConfig[currentTheme.value]?.icon || 'lucide:moon')
const themeLabel = computed(() => themeConfig[currentTheme.value]?.label || '深色')

// 应用主题到 HTML
const applyTheme = (theme: ThemeType) => {
  const html = document.documentElement
  // 移除所有主题 class
  html.classList.remove('dark', 'ocean', 'warm')
  // 添加新主题 class（light 不需要 class）
  if (theme !== 'light') {
    html.classList.add(theme)
  }
}

// 切换主题
const handleThemeChange = (theme: ThemeType) => {
  currentTheme.value = theme
  localStorage.setItem(THEME_STORAGE_KEY, theme)
  applyTheme(theme)
}

// 用户信息
const userName = computed(() => userStore.user?.username || '用户')
const userEmail = computed(() => userStore.user?.email || '')
const userAvatar = computed(() => userStore.user?.avatar_url || '')
const userInitial = computed(() => userName.value.charAt(0).toUpperCase())

// 未读通知数量
const unreadCount = ref(0) // TODO: 从 API 获取

// Menu routes - 过滤掉 hidden 的路由
const menuRoutes = computed(() => {
  const mainRoute = router.getRoutes().find((r) => r.path === '/')
  return mainRoute?.children?.filter((route) => !route.meta?.hidden) || []
})

// 根据分组获取路由
const getGroupRoutes = (groupKey: string) => {
  return menuRoutes.value.filter((route) => route.meta?.group === groupKey)
}

// Active menu and current title
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta?.title as string) || '')

// Actions
const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}

const handleRefresh = () => {
  router.go(0)
}

const goToNotifications = () => {
  router.push('/notifications')
}

const handleUserMenuCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
  }
}

// Router navigation hooks for loading bar
let removeBeforeEach: (() => void) | null = null
let removeAfterEach: (() => void) | null = null

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', () => {
    isMobile.value = window.innerWidth <= 768
  })

  // 初始化主题
  applyTheme(currentTheme.value)
  
  // Start loading bar on route change
  removeBeforeEach = router.beforeEach((to, from, next) => {
    loadingBarRef.value?.start()
    next()
  })

  // Finish loading bar after route change
  removeAfterEach = router.afterEach(() => {
    setTimeout(() => {
      loadingBarRef.value?.finish()
    }, 100)
  })
})

onUnmounted(() => {
  // Cleanup navigation guards
  removeBeforeEach?.()
  removeAfterEach?.()
})
</script>

<style scoped>
.main-layout {
  width: 100%;
  height: 100vh;
  background-color: var(--bg-color, #F8FAFC);
}

/* ========== 侧边栏  一体化风格 ========== */
.sidebar {
  background: var(--bg-color-sidebar, #FFFFFF);
  border-right: 1px solid var(--border-color, #E2E8F0);
  transition: width var(--transition-base, 250ms) var(--ease-in-out-smooth);
  box-shadow: none;
  display: flex;
  flex-direction: column;
}

/* Logo区域 - 简洁优雅 */
.logo {
  height: var(--header-height, 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border-color, #E2E8F0);
  padding: 0 var(--spacing-md, 16px);
  flex-shrink: 0;
}

.logo h2 {
  font-size: 20px;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.logo-collapsed {
  font-size: 24px !important;
}

.menu-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--spacing-sm, 8px) 0;
}

/* 分组标题 - 更柔和 */
.menu-group-title {
  padding: 16px 16px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-color-muted, #94A3B8);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-top: 4px;
}

.menu-group-title:first-child {
  margin-top: 0;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
}

/* ========== 菜单项 - 优雅交互 ========== */
.sidebar-menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 1;
  display: flex;
  align-items: center;
  border-radius: 8px;
  margin: 2px 8px;
  padding: 0 10px !important;
  color: var(--text-color-secondary, #64748B);
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast, 150ms) var(--ease-in-out-smooth);
  position: relative;
}

.sidebar-menu :deep(.el-menu-item .el-icon),
.sidebar-menu :deep(.el-menu-item .app-icon) {
  flex-shrink: 0;
  margin-right: 10px;
  color: inherit;
}

/* 悬停状态 - 柔和背景 */
.sidebar-menu :deep(.el-menu-item):hover {
  background: var(--bg-color-sidebar-hover, #F1F5F9) !important;
  color: var(--text-color-primary, #1E293B);
  transform: none;
}

/* 选中状态 - 左侧指示条 + 浅蓝背景 */
.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--bg-color-sidebar-active, rgba(59, 130, 246, 0.08)) !important;
  color: var(--primary-color, #3B82F6);
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--primary-color, #3B82F6);
  border-radius: 0 3px 3px 0;
}

/* ========== Header - 一体化风格 ========== */
.header {
  background-color: var(--bg-color-light, #FFFFFF);
  border-bottom: 1px solid var(--border-color, #E2E8F0);
  height: var(--header-height, 60px) !important;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg, 24px);
  box-shadow: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg, 24px);
}

.header-left :deep(.el-breadcrumb) {
  line-height: 1;
}

.header-left :deep(.el-breadcrumb__item) {
  display: flex;
  align-items: center;
  line-height: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 16px);
}

.collapse-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-color-secondary, #64748B);
  transition: color var(--transition-fast, 150ms);
  padding: 6px;
  border-radius: 6px;
  line-height: 1;
}

.collapse-icon:hover {
  color: var(--primary-color, #3B82F6);
  background: var(--bg-color-overlay, #F1F5F9);
}

.user-avatar-wrapper {
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: opacity var(--transition-fast, 150ms);
}

.user-avatar-wrapper:hover {
  opacity: 0.85;
}

.user-info-item {
  cursor: default !important;
}

.user-info {
  padding: 4px 0;
}

.user-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-color-primary, #1E293B);
}

.user-email {
  font-size: 12px;
  color: var(--text-color-secondary, #64748B);
  margin-top: 2px;
}

/* ========== Main Content ========== */
.main-content {
  background-color: var(--bg-color, #F8FAFC);
  padding: var(--spacing-lg, 24px);
}

.main-content.no-padding {
  padding: 0;
}

/* ========== 页面过渡动画 ========== */
.page-enter-active {
  animation: pageSlideIn 0.3s var(--ease-in-out-smooth);
}

.page-leave-active {
  animation: pageSlideOut 0.2s var(--ease-in-out-smooth);
}

@keyframes pageSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes pageSlideOut {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(-10px) scale(0.99);
  }
}

/* ========== 页面级 Tab 栏样式 ========== */
.page-tabs-bar {
  transition: all var(--transition-slow, 300ms) var(--ease-in-out-smooth);
  overflow: visible;
}

/* 卡片悬浮样式 (默认) */
.page-tabs-card {
  background-color: var(--bg-color, #F8FAFC);
  border-bottom: none;
  padding: 0 var(--spacing-lg, 24px);
  min-height: 56px;
  display: flex;
  align-items: center;
}

.page-tabs-card :deep(.page-level-tabs) {
  width: 100%;

  .el-tabs__header {
    margin-bottom: 0;
    background: transparent;
    border-radius: 0;
    padding: 0;
    box-shadow: none;
    border: none;
    border-bottom: none;
    transition: all var(--transition-base, 200ms) var(--ease-in-out-smooth);
    display: flex;
    align-items: center;
    height: 56px;
  }

  .el-tabs__header:hover {
    background: transparent;
  }

  .el-tabs__nav-wrap {
    display: flex;
    align-items: center;
    height: 56px;
  }

  .el-tabs__nav-wrap::after {
    height: 0;
  }

  .el-tabs__active-bar {
    display: none !important;
  }

  .el-tabs__item {
    font-size: 14px;
    font-weight: 500;
    height: 40px;
    line-height: 40px;
    padding: 0 16px;
    margin: 0 4px;
    border-radius: 6px;
    transition: all var(--transition-fast, 150ms) var(--ease-in-out-smooth);
    color: var(--text-color-secondary, #64748B);
    border: none;
    background: transparent;
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .el-tabs__item:hover {
    color: var(--primary-color, #3B82F6);
    background: transparent;
    transform: none;
    box-shadow: none;
  }

  .el-tabs__item.is-active {
    color: var(--primary-color, #3B82F6);
    font-weight: 600;
    background: transparent;
    border: none;
    transform: none;
    box-shadow: none;
    position: relative;
  }

  .el-tabs__item.is-active::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 12px;
    right: 12px;
    height: 2px;
    background: var(--primary-color, #3B82F6);
    border-radius: 1px;
  }

  .el-tabs__content {
    display: none;
  }

  .tab-label {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tab-label .el-icon {
    font-size: 16px;
    transition: transform var(--transition-fast, 150ms);
  }

  .el-tabs__item:hover .tab-label .el-icon {
    transform: scale(1.05);
  }
}

/* 胶囊式样式 */
.page-tabs-pill {
  background-color: transparent;
  border-bottom: none;
  padding: var(--spacing-md, 16px) var(--spacing-lg, 24px) var(--spacing-sm, 8px);
  min-height: 72px;
  display: flex;
  align-items: center;
}

.page-tabs-pill :deep(.page-level-tabs) {
  .el-tabs__header {
    margin-bottom: 0;
    background: var(--bg-color-overlay, #F1F5F9);
    border-radius: 9999px;
    padding: 6px;
    display: inline-flex;
    box-shadow: var(--box-shadow-sm);
  }

  .el-tabs__nav-wrap {
    border-radius: 9999px;
  }

  .el-tabs__nav-wrap::after {
    height: 0;
  }

  .el-tabs__active-bar {
    display: none !important;
  }

  .el-tabs__item {
    font-size: 14px;
    font-weight: 500;
    height: 40px;
    line-height: 40px;
    padding: 0 24px;
    margin: 0 2px;
    border-radius: 9999px;
    transition: all var(--transition-base, 200ms) var(--ease-in-out-smooth);
    color: var(--text-color-secondary, #64748B);
  }

  .el-tabs__item:hover {
    background: rgba(59, 130, 246, 0.08);
    color: var(--primary-color, #3B82F6);
    transform: scale(1.02);
  }

  .el-tabs__item.is-active {
    background: var(--primary-color, #3B82F6);
    color: white;
    font-weight: 600;
    box-shadow: var(--box-shadow-primary);
    transform: scale(1);
  }

  .el-tabs__item .el-icon {
    margin-right: 6px;
    transition: transform var(--transition-fast, 150ms);
  }

  .el-tabs__item.is-active .el-icon {
    transform: scale(1.05);
  }

  .el-tabs__content {
    display: none;
  }

  .tab-label {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tab-label .el-icon {
    font-size: 16px;
  }
}


/* Mobile Responsive */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 2000;
    height: 100%;
  }

  .sidebar-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1999;
    backdrop-filter: blur(2px);
  }

  .header {
    padding: 0 12px;
  }

  .header-left {
    gap: 12px;
    min-width: 0;
    flex: 1;
    overflow: hidden;
  }

  /* 移动端隐藏侧边栏折叠按钮（底部"更多"面板替代侧边栏导航） */
  .collapse-icon {
    display: none;
  }

  /* Truncate breadcrumb on mobile */
  .header-left :deep(.el-breadcrumb) {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    max-width: 140px;
  }

  .header-right {
    gap: 6px;
    flex-shrink: 0;
  }

  /* Main content: reduce padding, add bottom space for bottom nav */
  .main-content {
    padding: 16px;
    padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px) + 16px);
  }

  .main-content.no-padding {
    padding: 0;
    padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px));
  }

  /* Page tabs: make scrollable on mobile */
  .page-tabs-bar {
    overflow-x: auto;
    overflow-y: visible;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }

  .page-tabs-bar::-webkit-scrollbar {
    display: none;
  }

  .page-tabs-card {
    padding: 0 8px;
  }

  .page-tabs-pill {
    padding: var(--spacing-sm, 8px) var(--spacing-sm, 8px) 6px;
  }
}
</style>
