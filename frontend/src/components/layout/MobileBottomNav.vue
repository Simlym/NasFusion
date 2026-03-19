<template>
  <nav class="mobile-bottom-nav">
    <!-- 核心 Tab -->
    <router-link
      v-for="item in coreTabs"
      :key="item.path"
      :to="item.path"
      class="nav-item"
      :class="{ active: isTabActive(item.path, item.exact) }"
    >
      <AppIcon :name="item.icon" :size="22" class="nav-icon" />
      <span class="nav-label">{{ item.label }}</span>
    </router-link>

    <!-- 更多 按钮 -->
    <button
      class="nav-item nav-more"
      :class="{ active: isMoreActive }"
      @click="openMore"
    >
      <AppIcon name="lucide:ellipsis" :size="22" class="nav-icon" />
      <span class="nav-label">更多</span>
    </button>
  </nav>

  <!-- 更多面板 Overlay -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showMore" class="more-overlay" @click="closeMore" />
    </Transition>

    <Transition name="slide-up">
      <div v-if="showMore" class="more-sheet">
        <!-- 拖拽手柄 -->
        <div class="more-handle" />

        <!-- 标题栏 -->
        <div class="more-header">
          <span class="more-title">导航</span>
          <button class="more-close" @click="closeMore">
            <AppIcon name="lucide:x" :size="16" />
          </button>
        </div>

        <!-- 分类导航 -->
        <div class="more-body">
          <div
            v-for="group in moreGroups"
            :key="group.key"
            class="more-group"
          >
            <div class="more-group-label">{{ group.label }}</div>
            <div class="more-group-items">
              <router-link
                v-for="item in group.items"
                :key="item.path"
                :to="item.path"
                class="more-item"
                :class="{ active: isTabActive(item.path, false) }"
                @click="closeMore"
              >
                <div class="more-item-icon">
                  <AppIcon :name="item.icon" :size="22" />
                </div>
                <span class="more-item-label">{{ item.label }}</span>
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'

const route = useRoute()
const showMore = ref(false)

// 底部核心 Tab
const coreTabs = [
  { path: '/dashboard', icon: 'lucide:home', label: '首页', exact: true },
  { path: '/resource-library', icon: 'lucide:clapperboard', label: '资源库', exact: false },
  { path: '/subscriptions', icon: 'lucide:rss', label: '订阅', exact: false },
  { path: '/ai-agent', icon: 'lucide:bot', label: 'AI', exact: false },
]

// "更多" 中的路径前缀列表（用于判断是否激活）
const morePaths = [
  '/resources',
  '/persons',
  '/downloads',
  '/files',
  '/media-servers',
  '/tasks',
  '/notifications',
  '/system-logs',
  '/settings',
  '/storage-mounts',
]

// 更多面板分组
const moreGroups = [
  {
    key: 'discover',
    label: '发现',
    items: [
      { path: '/resources', icon: 'lucide:compass', label: '资源发现' },
      { path: '/persons', icon: 'lucide:users', label: '演员库' },
    ],
  },
  {
    key: 'media',
    label: '媒体',
    items: [
      { path: '/downloads', icon: 'lucide:download', label: '下载中心' },
      { path: '/files', icon: 'lucide:folder-open', label: '文件管理' },
      { path: '/media-servers', icon: 'lucide:tv-minimal', label: '媒体服务器' },
    ],
  },
  {
    key: 'tools',
    label: '工具',
    items: [
      { path: '/tasks', icon: 'lucide:list-checks', label: '任务中心' },
      { path: '/notifications', icon: 'lucide:bell', label: '通知中心' },
    ],
  },
  {
    key: 'system',
    label: '系统',
    items: [
      { path: '/system-logs', icon: 'lucide:file-text', label: '系统日志' },
      { path: '/settings', icon: 'lucide:settings', label: '系统设置' },
    ],
  },
]

const isTabActive = (path: string, exact: boolean) => {
  if (exact) return route.path === path
  return route.path.startsWith(path)
}

// 当前路由在"更多"列表中时，更多按钮高亮
const isMoreActive = computed(() =>
  morePaths.some(p => route.path.startsWith(p))
)

const openMore = () => {
  showMore.value = true
}

const closeMore = () => {
  showMore.value = false
}
</script>

<style scoped>
/* ─── 底部导航栏 ─── */
.mobile-bottom-nav {
  display: none;
}

@media (max-width: 768px) {
  .mobile-bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: calc(56px + env(safe-area-inset-bottom, 0px));
    background-color: var(--nf-bg-base, #ffffff);
    border-top: 1px solid var(--nf-border-light, #E2E8F0);
    display: flex;
    align-items: stretch;
    z-index: 1998;
    box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.08);
  }
}

/* nav-item 通用（router-link 和 button） */
.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: var(--nf-text-secondary, #64748B);
  transition: color 0.2s, background-color 0.15s;
  padding: 6px 4px;
  min-width: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  font-family: inherit;
}

.nav-item:active {
  background-color: var(--nf-bg-overlay, #F1F5F9);
}

.nav-item.active {
  color: var(--nf-primary, #3B82F6);
}

.nav-icon {
  font-size: 20px;
  flex-shrink: 0;
  transition: transform 0.15s;
}

.nav-item.active .nav-icon {
  transform: scale(1.1);
}

.nav-label {
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  line-height: 1;
}

/* ─── 更多面板 Overlay ─── */
.more-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 2001;
  backdrop-filter: blur(2px);
}

/* ─── 更多面板 Sheet ─── */
.more-sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2002;
  background: var(--nf-bg-elevated, #ffffff);
  border-radius: 16px 16px 0 0;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.12);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.more-handle {
  width: 36px;
  height: 4px;
  background: var(--nf-border-base, #CBD5E1);
  border-radius: 2px;
  margin: 10px auto 0;
  flex-shrink: 0;
}

.more-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 8px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--nf-border-light, #F1F5F9);
}

.more-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--nf-text-primary, #1E293B);
}

.more-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: var(--nf-bg-overlay, #F1F5F9);
  border-radius: 50%;
  cursor: pointer;
  color: var(--nf-text-secondary, #64748B);
  -webkit-tap-highlight-color: transparent;
  font-size: 14px;
}

.more-close:active {
  opacity: 0.7;
}

/* ─── 更多面板内容 ─── */
.more-body {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 8px 16px 16px;
  flex: 1;
}

.more-group {
  margin-bottom: 16px;
}

.more-group:last-child {
  margin-bottom: 0;
}

.more-group-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--nf-text-placeholder, #94A3B8);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 6px;
  padding-left: 2px;
}

.more-group-items {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}

.more-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 10px 4px;
  text-decoration: none;
  color: var(--nf-text-secondary, #64748B);
  border-radius: 10px;
  transition: background-color 0.15s, color 0.15s;
  -webkit-tap-highlight-color: transparent;
  min-width: 0;
}

.more-item:active {
  background-color: var(--nf-bg-overlay, #F1F5F9);
}

.more-item.active {
  color: var(--nf-primary, #3B82F6);
  background-color: rgba(59, 130, 246, 0.08);
}

.more-item-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--nf-bg-overlay, #F1F5F9);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: background-color 0.15s;
  flex-shrink: 0;
}

.more-item.active .more-item-icon {
  background: rgba(59, 130, 246, 0.12);
}

.more-item-label {
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  line-height: 1.2;
  text-align: center;
}

/* ─── 动画 ─── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.22s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}
</style>
