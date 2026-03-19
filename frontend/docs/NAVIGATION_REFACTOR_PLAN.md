# NasFusion 导航架构重构方案

> **制定日期**: 2025-11-18
> **目标**: 优化信息架构，提升导航清晰度和用户体验

---

## 📊 当前问题分析

### 现有菜单结构（14项）
```
✓ 仪表盘
✓ PT站点          ← 配置类
✓ PT资源          ← 原始数据
✓ 电影资源        ← 媒体类型（仅1个）
✓ 下载管理        ← 功能
✓ 媒体文件        ← 功能
✓ 整理配置        ← 配置类
✓ 订阅管理        ← 功能
✓ 任务管理        ← 系统
✓ 通知中心        ← 系统
✓ 用户管理        ← 管理（仅管理员）
✓ 个人设置        ← 应该在右上角
✓ 系统设置        ← 配置类
```

### 存在的问题
- ❌ 功能与配置混杂，无分组
- ❌ 个人设置在侧边栏，不符合用户习惯
- ❌ 缺少其他媒体类型（剧集、动画、音乐、书籍）
- ❌ 如果为每个媒体类型创建菜单项，会有 5-6 个类似项
- ❌ 重复图标（VideoCamera×2, Setting×2）

---

## 🎯 新导航架构（方案B）

### 侧边栏菜单（7项，分2组）

```
━━━━━━━━━━━━━━━━━━━━━
  核心功能
━━━━━━━━━━━━━━━━━━━━━
📊 仪表盘           /dashboard
🎬 媒体库           /media-library
                    ├─ Tab: 电影
                    ├─ Tab: 剧集
                    ├─ Tab: 动画
                    ├─ Tab: 音乐
                    └─ Tab: 电子书
📥 下载中心         /downloads
⭐ 订阅管理         /subscriptions
📦 资源发现         /resources (原PT资源)

━━━━━━━━━━━━━━━━━━━━━
  管理
━━━━━━━━━━━━━━━━━━━━━
📋 任务中心         /tasks
⚙️ 系统设置         /settings
                    ├─ Tab: PT站点
                    ├─ Tab: 整理规则
                    ├─ Tab: 下载器
                    ├─ Tab: 系统配置
                    └─ Tab: 用户管理（仅管理员）
```

### 右上角区域

```
[🔄] [🔔 (3)] [🌓] [👤 ▼]
 │     │      │      └─ 个人资料
 │     │      │      └─ 账号设置
 │     │      │      └─ 退出登录
 │     │      └─ 深色模式切换
 │     └─ 通知中心（带未读数量）
 └─ 刷新当前页面
```

---

## 🗂️ 路由结构设计

### 新路由配置

```typescript
const routes = [
  {
    path: '/login',
    name: 'Login',
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      // ========== 核心功能 ==========
      {
        path: '/dashboard',
        name: 'Dashboard',
        meta: {
          title: '仪表盘',
          icon: 'DataLine',
          group: 'core' // 分组标识
        }
      },
      {
        path: '/media-library',
        name: 'MediaLibrary',
        meta: {
          title: '媒体库',
          icon: 'VideoCamera',
          group: 'core'
        },
        redirect: '/media-library/movies',
        children: [
          // 子路由支持直接访问
          { path: 'movies', name: 'Movies', meta: { tab: 'movies' } },
          { path: 'tv', name: 'TVSeries', meta: { tab: 'tv' } },
          { path: 'anime', name: 'Anime', meta: { tab: 'anime' } },
          { path: 'music', name: 'Music', meta: { tab: 'music' } },
          { path: 'books', name: 'Books', meta: { tab: 'books' } }
        ]
      },
      {
        path: '/movies/:id',
        name: 'MovieDetail',
        meta: { hidden: true } // 不在菜单中显示
      },
      {
        path: '/downloads',
        name: 'Downloads',
        meta: {
          title: '下载中心',
          icon: 'Download',
          group: 'core'
        }
      },
      {
        path: '/subscriptions',
        name: 'Subscriptions',
        meta: {
          title: '订阅管理',
          icon: 'Star',
          group: 'core'
        }
      },
      {
        path: '/resources',
        name: 'Resources',
        meta: {
          title: '资源发现',
          icon: 'Search',
          group: 'core'
        }
      },

      // ========== 管理 ==========
      {
        path: '/tasks',
        name: 'Tasks',
        meta: {
          title: '任务中心',
          icon: 'List',
          group: 'management'
        }
      },
      {
        path: '/settings',
        name: 'Settings',
        meta: {
          title: '系统设置',
          icon: 'Setting',
          group: 'management'
        }
      },

      // ========== 个人（右上角菜单，不在侧边栏） ==========
      {
        path: '/profile',
        name: 'Profile',
        meta: {
          title: '个人资料',
          hidden: true // 不在侧边栏显示
        }
      },
      {
        path: '/notifications',
        name: 'Notifications',
        meta: {
          title: '通知中心',
          hidden: true // 右上角图标入口
        }
      }
    ]
  }
]
```

### 分组定义

```typescript
// router/groups.ts
export const menuGroups = [
  {
    key: 'core',
    label: '核心功能',
    order: 1
  },
  {
    key: 'management',
    label: '管理',
    order: 2
  }
]
```

---

## 🧩 组件改造方案

### 1. MainLayout.vue 改造

#### 左侧菜单 - 支持分组

```vue
<template>
  <el-aside :width="sidebarWidth" class="sidebar">
    <!-- Logo -->
    <div class="logo">
      <h2>NasFusion</h2>
    </div>

    <!-- 菜单 - 按分组显示 -->
    <div class="menu-container">
      <template v-for="group in menuGroups" :key="group.key">
        <!-- 分组标题 -->
        <div class="menu-group-title">{{ group.label }}</div>

        <!-- 该分组的菜单项 -->
        <el-menu
          :default-active="activeMenu"
          router
          :collapse="isCollapse"
        >
          <el-menu-item
            v-for="route in getGroupRoutes(group.key)"
            :key="route.path"
            :index="route.path"
          >
            <el-icon><component :is="route.meta?.icon" /></el-icon>
            <template #title>{{ route.meta?.title }}</template>
          </el-menu-item>
        </el-menu>
      </template>
    </div>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { menuGroups } from '@/router/groups'

const getGroupRoutes = (groupKey: string) => {
  return menuRoutes.value.filter(
    route => route.meta?.group === groupKey && !route.meta?.hidden
  )
}
</script>

<style scoped>
.menu-group-title {
  padding: 16px 20px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 收起状态隐藏分组标题 */
.el-menu--collapse + .menu-group-title {
  display: none;
}
</style>
```

#### 右上角 - 头像下拉菜单

```vue
<template>
  <el-header class="header">
    <div class="header-left">
      <el-icon class="collapse-icon" @click="toggleSidebar">
        <Fold v-if="!isCollapse" />
        <Expand v-else />
      </el-icon>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="header-right">
      <!-- 刷新按钮 -->
      <el-button
        type="default"
        :icon="Refresh"
        circle
        @click="handleRefresh"
        title="刷新"
      />

      <!-- 通知中心 -->
      <el-badge :value="unreadCount" :hidden="unreadCount === 0">
        <el-button
          type="default"
          :icon="Bell"
          circle
          @click="goToNotifications"
          title="通知中心"
        />
      </el-badge>

      <!-- 深色模式切换 -->
      <el-button
        type="default"
        :icon="isDark ? Sunny : Moon"
        circle
        @click="toggleDarkMode"
        :title="isDark ? '切换到亮色模式' : '切换到深色模式'"
      />

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
            <el-dropdown-item divided command="profile" :icon="User">
              个人资料
            </el-dropdown-item>
            <el-dropdown-item command="settings" :icon="Setting">
              账号设置
            </el-dropdown-item>
            <el-dropdown-item divided command="logout" :icon="SwitchButton">
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Fold, Expand, Refresh, Bell, Moon, Sunny,
  User, Setting, SwitchButton
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

// 用户信息
const userName = computed(() => userStore.user?.username || '用户')
const userEmail = computed(() => userStore.user?.email || '')
const userAvatar = computed(() => userStore.user?.avatar || '')
const userInitial = computed(() => userName.value.charAt(0).toUpperCase())

// 未读通知数量
const unreadCount = ref(0) // 从 API 获取

// 导航到通知中心
const goToNotifications = () => {
  router.push('/notifications')
}

// 处理用户菜单命令
const handleUserMenuCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style scoped>
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar-wrapper {
  cursor: pointer;
  display: flex;
  align-items: center;
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
  color: var(--text-color-primary);
}

.user-email {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-top: 2px;
}
</style>
```

---

### 2. MediaLibrary.vue 组件

统一的媒体库入口，使用 Tab 切换不同媒体类型。

```vue
<template>
  <div class="media-library-container">
    <PageHeader
      title="媒体库"
      description="浏览和管理所有媒体资源"
    >
      <template #extra>
        <el-button type="primary" :icon="Plus">
          添加资源
        </el-button>
      </template>
    </PageHeader>

    <el-card class="media-tabs-card">
      <el-tabs
        v-model="activeTab"
        @tab-change="handleTabChange"
        class="media-tabs"
      >
        <el-tab-pane label="🎬 电影" name="movies">
          <MoviesView />
        </el-tab-pane>

        <el-tab-pane label="📺 剧集" name="tv">
          <TVSeriesView />
        </el-tab-pane>

        <el-tab-pane label="🎭 动画" name="anime">
          <AnimeView />
        </el-tab-pane>

        <el-tab-pane label="🎵 音乐" name="music">
          <MusicView />
        </el-tab-pane>

        <el-tab-pane label="📚 电子书" name="books">
          <BooksView />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/common/PageHeader.vue'
import MoviesView from '@/components/media/MoviesView.vue'
import TVSeriesView from '@/components/media/TVSeriesView.vue'
import AnimeView from '@/components/media/AnimeView.vue'
import MusicView from '@/components/media/MusicView.vue'
import BooksView from '@/components/media/BooksView.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref<string>('movies')

// 根据子路由设置当前 Tab
onMounted(() => {
  const tab = route.meta.tab as string
  if (tab) {
    activeTab.value = tab
  }
})

// 监听路由变化
watch(() => route.meta.tab, (newTab) => {
  if (newTab) {
    activeTab.value = newTab as string
  }
})

// Tab 切换时更新路由
const handleTabChange = (tabName: string) => {
  router.push(`/media-library/${tabName}`)
}
</script>

<style scoped>
.media-library-container {
  padding: var(--spacing-lg);
}

.media-tabs-card {
  margin-top: var(--spacing-lg);
}

.media-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--spacing-lg);
}

.media-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
  padding: 0 24px;
  height: 48px;
  line-height: 48px;
}
</style>
```

---

### 3. Settings.vue 多 Tab 结构

```vue
<template>
  <div class="settings-container">
    <PageHeader
      title="系统设置"
      description="配置PT站点、整理规则和系统参数"
    />

    <el-card class="settings-tabs-card">
      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- PT站点配置 -->
        <el-tab-pane label="PT站点" name="sites">
          <SitesSettings />
        </el-tab-pane>

        <!-- 整理规则 -->
        <el-tab-pane label="整理规则" name="organize">
          <OrganizeSettings />
        </el-tab-pane>

        <!-- 下载器配置 -->
        <el-tab-pane label="下载器" name="downloader">
          <DownloaderSettings />
        </el-tab-pane>

        <!-- 系统配置 -->
        <el-tab-pane label="系统配置" name="system">
          <SystemSettings />
        </el-tab-pane>

        <!-- 用户管理（仅管理员） -->
        <el-tab-pane
          v-if="isAdmin"
          label="用户管理"
          name="users"
        >
          <UsersManagement />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import PageHeader from '@/components/common/PageHeader.vue'
import SitesSettings from '@/components/settings/SitesSettings.vue'
import OrganizeSettings from '@/components/settings/OrganizeSettings.vue'
import DownloaderSettings from '@/components/settings/DownloaderSettings.vue'
import SystemSettings from '@/components/settings/SystemSettings.vue'
import UsersManagement from '@/components/settings/UsersManagement.vue'

const userStore = useUserStore()
const activeTab = ref('sites')

const isAdmin = computed(() => userStore.user?.is_admin || false)
</script>

<style scoped>
.settings-container {
  padding: var(--spacing-lg);
}

.settings-tabs-card {
  margin-top: var(--spacing-lg);
}
</style>
```

---

## 📝 实施步骤

### Phase 1: 路由重构（30分钟）
- [ ] 创建 `router/groups.ts` 定义分组
- [ ] 修改 `router/index.ts`
  - 添加 `group` 元数据
  - 调整路由结构（媒体库子路由）
  - 标记 `hidden` 路由（个人资料、通知中心）
- [ ] 更新路由守卫逻辑

### Phase 2: MainLayout 改造（1小时）
- [ ] 修改左侧菜单支持分组显示
- [ ] 添加右上角头像下拉菜单
- [ ] 添加通知图标（带 Badge）
- [ ] 调整样式和交互
- [ ] 移除个人设置菜单项

### Phase 3: MediaLibrary 组件（1小时）
- [ ] 创建 `views/MediaLibrary.vue`
- [ ] 创建子组件（或复用现有 Movies.vue）
  - `components/media/MoviesView.vue`
  - `components/media/TVSeriesView.vue`
  - `components/media/AnimeView.vue`
  - `components/media/MusicView.vue`
  - `components/media/BooksView.vue`
- [ ] 实现 Tab 切换逻辑
- [ ] 路由与 Tab 联动

### Phase 4: Settings 整合（30分钟）
- [ ] 修改 `views/Settings.vue` 为多 Tab 结构
- [ ] 拆分设置内容为子组件
  - `components/settings/SitesSettings.vue` (原 Sites.vue 内容)
  - `components/settings/OrganizeSettings.vue` (原 OrganizeConfigs.vue 内容)
  - `components/settings/DownloaderSettings.vue`
  - `components/settings/SystemSettings.vue`
  - `components/settings/UsersManagement.vue` (原 Users.vue 内容)
- [ ] 处理管理员权限判断

### Phase 5: 清理旧代码（15分钟）
- [ ] 删除或重命名旧视图文件
  - `views/Sites.vue` → 移到 `components/settings/`
  - `views/OrganizeConfigs.vue` → 移到 `components/settings/`
  - `views/Users.vue` → 移到 `components/settings/`
- [ ] 删除 `views/Media.vue`（功能合并到 MediaLibrary）

### Phase 6: 测试（30分钟）
- [ ] 测试所有菜单链接
- [ ] 测试 Tab 切换和路由联动
- [ ] 测试直接访问子路由（如 `/media-library/movies`）
- [ ] 测试头像下拉菜单
- [ ] 测试权限（管理员 vs 普通用户）
- [ ] 测试响应式布局

---

## 🎨 样式规范

### 菜单分组标题
```css
.menu-group-title {
  padding: 16px 20px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-color-light);
  margin-bottom: 8px;
}
```

### 用户头像下拉菜单
```css
.user-avatar-wrapper {
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.user-avatar-wrapper:hover {
  opacity: 0.8;
}

.el-avatar {
  border: 2px solid var(--border-color);
  transition: border-color var(--transition-fast);
}

.user-avatar-wrapper:hover .el-avatar {
  border-color: var(--primary-color);
}
```

---

## ✅ 验收标准

### 功能
- [ ] 侧边栏菜单按分组显示（核心功能、管理）
- [ ] 媒体库支持 Tab 切换 5 种媒体类型
- [ ] 系统设置支持 Tab 切换多个配置项
- [ ] 右上角头像菜单正常工作
- [ ] 通知图标显示未读数量
- [ ] 路由与 Tab 联动正确

### 用户体验
- [ ] 菜单项数量从 13 个减少到 7 个
- [ ] 分组清晰，功能定位明确
- [ ] 个人相关功能在右上角，符合用户习惯
- [ ] 媒体类型集中在一个入口，便于浏览

### 性能
- [ ] 页面切换流畅
- [ ] Tab 切换无延迟
- [ ] 无控制台错误

---

## 📊 前后对比

| 指标 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| 侧边栏菜单项 | 13个 | 7个 | ↓ 46% |
| 菜单分组 | 无 | 2个 | ✅ |
| 媒体类型入口 | 1个（仅电影） | 1个（5种类型） | ✅ |
| 设置分散程度 | 4个独立菜单项 | 1个（5个Tab） | ↓ 75% |
| 个人设置位置 | 侧边栏 | 右上角 | ✅ |
| 通知入口 | 侧边栏 | 右上角图标 | ✅ |

---

## 🔮 未来扩展

### 可能的优化
1. **二级菜单折叠**（如果未来菜单项过多）
2. **自定义菜单顺序**（用户可拖拽调整）
3. **常用功能收藏**（Pin 到顶部）
4. **快捷键支持**（如 Cmd+K 快速导航）
5. **面包屑导航增强**（显示完整路径）

### 新媒体类型添加
添加新类型（如"纪录片"）只需：
1. 在 `MediaLibrary.vue` 添加一个 Tab
2. 创建对应的 View 组件
3. 添加子路由（可选）

---

**方案制定**: Claude
**预计实施时间**: 3-4 小时
**影响范围**: 路由、布局、多个视图组件
