import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import MainLayout from '@/components/layout/MainLayout.vue'
import { useUserStore } from '@/stores/user'

// 页面级标签栏配置类型
export interface PageTabConfig {
  name: string           // 标签名称（用于路由 query）
  label: string          // 显示文本
  icon?: string          // 图标名称（Iconify 格式，如 'lucide:film'）
}

export interface PageTabsConfig {
  enabled: boolean       // 是否启用页面级标签栏
  tabs: PageTabConfig[]  // 标签列表
  style?: 'card' | 'pill' | 'underline'  // 样式风格（card: 卡片悬浮, pill: 胶囊式, underline: 下划线）
  defaultTab?: string    // 默认激活的标签
}

// 扩展路由 meta 类型
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    icon?: string
    group?: string
    hidden?: boolean
    requiresAuth?: boolean
    pageTabs?: PageTabsConfig  // 页面级标签栏配置
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      // ========== 概览 ==========
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: {
          title: '首页',
          icon: 'lucide:home',
          group: 'overview'
        }
      },

      // ========== 发现 ==========
      {
        path: '/resources',
        name: 'Resources',
        component: () => import('@/views/Resources.vue'),
        meta: {
          title: '资源发现',
          icon: 'lucide:compass',
          group: 'discover'
        }
      },
      {
        path: '/resource-library',
        name: 'MediaLibrary',
        component: () => import('@/views/MediaLibrary.vue'),
        meta: {
          title: '资源库',
          icon: 'lucide:clapperboard',
          group: 'discover',
          pageTabs: {
            enabled: true,
            style: 'card',
            defaultTab: 'movies',
            tabs: [
              { name: 'movies', label: '电影', icon: 'lucide:film' },
              { name: 'tv', label: '剧集', icon: 'lucide:tv' },
              { name: 'anime', label: '动画', icon: 'lucide:sparkles' },
              { name: 'music', label: '音乐', icon: 'lucide:music' },
              { name: 'books', label: '电子书', icon: 'lucide:book-open' }
              // 注意：成人标签由 usePageTabs 根据后端配置动态添加
            ]
          }
        }
      },
      {
        path: '/persons',
        name: 'Persons',
        component: () => import('@/views/PersonList.vue'),
        meta: {
          title: '演员库',
          icon: 'lucide:users',
          group: 'discover'
        }
      },

      // ========== 媒体 ==========
      {
        path: '/subscriptions',
        name: 'Subscriptions',
        component: () => import('@/views/Subscriptions.vue'),
        meta: {
          title: '订阅管理',
          icon: 'lucide:rss',
          group: 'media'
        }
      },
      {
        path: '/downloads',
        name: 'Downloads',
        component: () => import('@/views/Downloads.vue'),
        meta: {
          title: '下载中心',
          icon: 'lucide:download',
          group: 'media',
          pageTabs: {
            enabled: true,
            style: 'card',
            defaultTab: 'tasks',
            tabs: [
              { name: 'tasks', label: '任务列表', icon: 'lucide:list' },
              { name: 'files', label: '下载目录', icon: 'lucide:folder' }
            ]
          }
        }
      },
      {
        path: '/files',
        name: 'Media',
        component: () => import('@/views/MediaFiles.vue'),
        meta: {
          title: '文件管理',
          icon: 'lucide:folder-open',
          group: 'media'
        }
      },
      {
        path: '/media-servers',
        name: 'MediaServers',
        component: () => import('@/views/MediaServers.vue'),
        meta: {
          title: '媒体服务器',
          icon: 'lucide:tv-minimal',
          group: 'media',
          pageTabs: {
            enabled: true,
            style: 'card',
            defaultTab: 'overview',
            tabs: [
              { name: 'overview', label: '概览', icon: 'lucide:bar-chart-2' },
              { name: 'history', label: '观看历史', icon: 'lucide:clock' },
              { name: 'library', label: '媒体库', icon: 'lucide:library' }
            ]
          }
        }
      },
      // ========== 工具 ==========
      {
        path: '/ai-agent',
        name: 'AIAgent',
        component: () => import('@/views/AIAgent.vue'),
        meta: {
          title: 'AI 助手',
          icon: 'lucide:bot',
          group: 'tools'
        }
      },
      {
        path: '/tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: {
          title: '任务中心',
          icon: 'lucide:list-checks',
          group: 'tools',
          pageTabs: {
            enabled: true,
            style: 'card',
            defaultTab: 'live-queue',
            tabs: [
              { name: 'live-queue', label: '实时队列', icon: 'lucide:activity' },
              { name: 'history', label: '历史记录', icon: 'lucide:history' },
              { name: 'scheduled', label: '定时任务', icon: 'lucide:alarm-clock-check' }
            ]
          }
        }
      },
      {
        path: '/notifications',
        name: 'Notifications',
        component: () => import('@/views/Notifications.vue'),
        meta: {
          title: '通知中心',
          icon: 'lucide:bell',
          group: 'tools'
        }
      },

      // ========== 系统 ==========
      {
        path: '/system-logs',
        name: 'SystemLogs',
        component: () => import('@/views/SystemLogs.vue'),
        meta: {
          title: '系统日志',
          icon: 'lucide:file-text',
          group: 'system'
        }
      },
      {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: {
          title: '系统设置',
          icon: 'lucide:settings',
          group: 'system',
          pageTabs: {
            enabled: true,
            style: 'card',
            defaultTab: 'system',
            tabs: [
              { name: 'system', label: '系统配置', icon: 'lucide:settings' },
              { name: 'storage', label: '存储管理', icon: 'lucide:hard-drive' },
              { name: 'pt-sites', label: 'PT站点', icon: 'lucide:globe' },
              { name: 'downloaders', label: '下载器', icon: 'lucide:download-cloud' },
              { name: 'media-servers', label: '媒体服务器', icon: 'lucide:tv-minimal' },
              { name: 'organize', label: '整理规则', icon: 'lucide:folder-sync' },
              { name: 'media-scraping', label: '媒体刮削', icon: 'lucide:scan-search' },
              { name: 'notifications', label: '通知设置', icon: 'lucide:bell-ring' },
              { name: 'login-security', label: '登录安全', icon: 'lucide:shield-check' }
            ]
          }
        }
      },
      {
        path: '/storage-mounts',
        name: 'StorageMounts',
        component: () => import('@/views/StorageMounts.vue'),
        meta: {
          title: '存储管理',
          icon: 'lucide:hard-drive',
          group: 'system',
          hidden: true
        }
      },


      // ========== 隐藏路由（不在侧边栏显示） ==========
      {
        path: '/resources/:id',
        name: 'ResourceDetail',
        component: () => import('@/views/ResourceDetail.vue'),
        meta: {
          title: '资源详情',
          hidden: true
        }
      },
      {
        path: '/movies/:id',
        name: 'MovieDetail',
        component: () => import('@/views/MovieDetail.vue'),
        meta: {
          title: '电影详情',
          hidden: true
        }
      },
      {
        path: '/tv/:id',
        name: 'TVSeriesDetail',
        component: () => import('@/views/TVSeriesDetail.vue'),
        meta: {
          title: '剧集详情',
          hidden: true
        }
      },
      {
        path: '/person/:id',
        name: 'PersonDetail',
        component: () => import('@/views/PersonDetail.vue'),
        meta: {
          title: '人员详情',
          hidden: true
        }
      },
      {
        path: '/profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: {
          title: '个人资料',
          hidden: true
        }
      },
      {
        path: '/subscriptions/:id',
        name: 'SubscriptionDetail',
        component: () => import('@/views/SubscriptionDetail.vue'),
        meta: {
          title: '订阅详情',
          hidden: true
        }
      },
      {
        path: '/notifications/rules',
        name: 'NotificationRules',
        component: () => import('@/views/NotificationRules.vue'),
        meta: {
          title: '通知规则管理',
          hidden: true
        }
      },
      {
        path: '/notifications/rules/:id',
        name: 'NotificationRuleDetail',
        component: () => import('@/views/NotificationRuleDetail.vue'),
        meta: {
          title: '通知规则详情',
          hidden: true
        }
      },
      {
        path: '/notifications/templates',
        name: 'NotificationTemplates',
        component: () => import('@/views/NotificationTemplates.vue'),
        meta: {
          title: '通知模板管理',
          hidden: true
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 配置滚动行为
  scrollBehavior(to, from, savedPosition) {
    // 如果有保存的滚动位置（浏览器前进/后退），恢复到该位置
    if (savedPosition) {
      return savedPosition
    }
    // 如果是从详情页返回媒体库，让组件自己处理滚动
    // （通过 keep-alive 和组件内部的滚动位置保存）
    if (from.name === 'MovieDetail' && to.name === 'MediaLibrary') {
      return false
    }
    if (from.name === 'TVSeriesDetail' && to.name === 'MediaLibrary') {
      return false
    }
    // 其他情况滚动到顶部
    return { top: 0, behavior: 'smooth' }
  }
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)

  if (requiresAuth) {
    const token = userStore.token

    if (!token) {
      // 没有 token，跳转登录
      return next({ name: 'Login', query: { redirect: to.fullPath } })
    }

    // 如果有 token 但没有用户信息，尝试获取
    if (!userStore.user) {
      try {
        await userStore.fetchCurrentUser()
      } catch (error) {
        // 获取用户信息失败（token 无效），清除并跳转登录
        console.error('Failed to fetch current user:', error)
        await userStore.logout()
        return next({ name: 'Login', query: { redirect: to.fullPath } })
      }
    }
  }

  if (to.name === 'Login' && userStore.isLoggedIn) {
    // 已登录用户访问登录页，跳转到首页
    return next({ name: 'Dashboard' })
  }

  next()
})

export default router
