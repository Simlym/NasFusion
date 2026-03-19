<template>
  <div class="dashboard-container">
    <div class="dashboard-main">
      <div class="dashboard-top-row">
        <!-- 1. 顶部 Hero (左/中/右三列) -->
        <div class="hero-section" @mouseenter="pauseCarousel" @mouseleave="resumeCarousel">
      <!-- 左：海报列 -->
      <div class="hero-poster" @click="navigateToHeroItem()">
        <!-- 骨架：纯色底色 -->
        <template v-if="heroLoading">
          <div class="hero-img-placeholder"></div>
        </template>
        <!-- 真实内容 -->
        <template v-else>
          <template v-if="currentHeroItem?.poster_url">
            <el-image
              :src="getProxiedImageUrl(currentHeroItem.poster_url)"
              fit="cover"
              style="width:100%;height:100%;display:block;"
            >
              <template #error><div class="poster-col-empty"><el-icon><Picture /></el-icon></div></template>
            </el-image>
          </template>
          <div class="poster-col-empty" v-else><el-icon><Picture /></el-icon></div>
          <div class="hero-poster-overlay" v-if="currentHeroItem">
            <div class="poster-ov-badges">
              <span class="poster-ov-type">{{ currentHeroItem.media_type === 'movie' ? '电影' : '剧集' }}</span>
              <span class="poster-ov-rating" v-if="currentHeroItem.rating">⭐ {{ currentHeroItem.rating.toFixed(1) }}</span>
            </div>
            <div class="poster-ov-title">{{ currentHeroItem.title }}</div>
            <div class="poster-ov-year" v-if="currentHeroItem.year">{{ currentHeroItem.year }}</div>
          </div>
        </template>
      </div>

      <!-- 中：Backdrop 图区 -->
      <div class="hero-left" :class="{ 'hero-left--welcome': !heroLoading && (forceEmpty || heroBackdrops.length === 0) }" @click="!forceEmpty && heroBackdrops.length > 0 ? navigateToHeroItem() : undefined">
        <!-- 骨架：纯色底色 -->
        <template v-if="heroLoading">
          <div class="hero-img-placeholder"></div>
        </template>
        <!-- 欢迎引导（空状态） -->
        <template v-else-if="forceEmpty || heroBackdrops.length === 0">
          <div class="welcome-pane">
            <div class="welcome-brand">
              <span class="welcome-logo">🎬</span>
              <span class="welcome-app-name">NasFusion</span>
            </div>
            <p class="welcome-tagline">三步完成配置，开启你的媒体中心</p>
            <div class="setup-steps">
              <div
                class="setup-step"
                :class="{ 'setup-step--done': !statsLoading && stats.sites > 0 }"
                @click.stop="navigateTo('/settings?tab=pt-sites')"
              >
                <div class="step-circle">
                  <span v-if="!statsLoading && stats.sites > 0">✓</span>
                  <span v-else>1</span>
                </div>
                <div class="step-body">
                  <div class="step-title">添加 PT 站点</div>
                  <div class="step-desc">连接 MTeam 等私有站点</div>
                </div>
                <div class="step-arrow">→</div>
              </div>
              <div
                class="setup-step"
                :class="{ 'setup-step--done': !statsLoading && stats.resources > 0 }"
                @click.stop="navigateTo('/tasks')"
              >
                <div class="step-circle">
                  <span v-if="!statsLoading && stats.resources > 0">✓</span>
                  <span v-else>2</span>
                </div>
                <div class="step-body">
                  <div class="step-title">同步 PT 资源</div>
                  <div class="step-desc">拉取并识别影视资源</div>
                </div>
                <div class="step-arrow">→</div>
              </div>
              <div
                class="setup-step"
                :class="{ 'setup-step--done': !statsLoading && stats.mediaServerCount > 0 }"
                @click.stop="navigateTo('/media-servers')"
              >
                <div class="step-circle">
                  <span v-if="!statsLoading && stats.mediaServerCount > 0">✓</span>
                  <span v-else>3</span>
                </div>
                <div class="step-body">
                  <div class="step-title">连接媒体服务器</div>
                  <div class="step-desc">Jellyfin / Emby / Plex</div>
                </div>
                <div class="step-arrow">→</div>
              </div>
            </div>
          </div>
        </template>
        <!-- 真实内容 -->
        <template v-else>
          <transition name="hero-bg-fade">
            <div class="hero-bg-layers" :key="currentHeroIndex">
              <!-- 底层：模糊 Poster，作为氛围背景，解决纵图 Backdrop 场景 -->
              <div class="hero-bg-blur" :style="heroBgBlurStyle"></div>
              <!-- 上层：Backdrop，cover 裁切，纵图时底层露出填充 -->
              <div class="hero-bg" :class="{ 'hero-bg--portrait': backdropIsPortrait }" :style="heroBgStyle"></div>
            </div>
          </transition>
          <div class="hero-left-edge"></div>
          <transition name="hero-info-fade">
            <div class="hero-info" v-if="currentHeroItem && currentHeroItem.overview" :key="currentHeroIndex">
              <div class="hero-info-overview">{{ currentHeroItem.overview }}</div>
            </div>
          </transition>
          <div class="hero-dots" v-if="heroBackdrops.length > 1">
            <span
              v-for="(_, i) in heroBackdrops" :key="i"
              class="hero-dot" :class="{ active: i === currentHeroIndex }"
              @click.stop="jumpToSlide(i)"
            ></span>
          </div>
        </template>
      </div>

      <!-- 右：指标面板（三行分组）- 结构始终显示，数字异步滚入 -->
      <div class="hero-right">
        <!-- 近期活动切换按钮（始终可见） -->
        <div class="activity-toggle-btn" @click="activityVisible = !activityVisible">
          <el-icon><DataLine /></el-icon>
        </div>

        <!-- 行 1：发现 -->
        <div class="stat-group">
          <div class="stat-group-label">发现</div>
          <div class="stat-group-row">
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/resources')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.resources.toLocaleString() }}
                </span>
                <span class="stat-badge" v-if="!statsLoading && todayStats.resources > 0">+{{ todayStats.resources }}</span>
              </div>
              <span class="stat-lbl">PT 资源</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/resource-library?tab=movies')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.movies.toLocaleString() }}
                </span>
                <span class="stat-badge" v-if="!statsLoading && todayStats.movies > 0">+{{ todayStats.movies }}</span>
              </div>
              <span class="stat-lbl">电影</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/resource-library?tab=tv')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.tvs.toLocaleString() }}
                </span>
                <span class="stat-badge" v-if="!statsLoading && todayStats.newTvs > 0">+{{ todayStats.newTvs }}</span>
              </div>
              <span class="stat-lbl">剧集</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/persons')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.actors.toLocaleString() }}
                </span>
                <span class="stat-badge" v-if="!statsLoading && todayStats.actors > 0">+{{ todayStats.actors }}</span>
              </div>
              <span class="stat-lbl">演员库</span>
            </div>
          </div>
        </div>

        <div class="stat-group-divider"></div>

        <!-- 行 2：媒体 -->
        <div class="stat-group">
          <div class="stat-group-label">媒体</div>
          <div class="stat-group-row">
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/subscriptions')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.subscriptions.toLocaleString() }}
                </span>
                <span class="stat-badge" v-if="!statsLoading && todayStats.subscriptions > 0">+{{ todayStats.subscriptions }}</span>
              </div>
              <span class="stat-lbl">订阅</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/downloads')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.totalDownloads.toLocaleString() }}
                </span>
                <span class="stat-badge" v-if="!statsLoading && todayStats.downloads > 0">+{{ todayStats.downloads }}</span>
              </div>
              <span class="stat-lbl">下载</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/files')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : formattedStorage }}
                </span>
              </div>
              <span class="stat-lbl">已用存储</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/media-servers')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.totalMediaItems.toLocaleString() }}
                </span>
              </div>
              <span class="stat-lbl">媒体服务器</span>
            </div>
          </div>
        </div>

        <div class="stat-group-divider"></div>

        <!-- 行 3：系统 -->
        <div class="stat-group">
          <div class="stat-group-label">系统</div>
          <div class="stat-group-row">
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/settings?tab=pt-sites')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.sites }}
                </span>
              </div>
              <span class="stat-lbl">PT 站点</span>
            </div>
            <div class="hero-stat-item hero-stat-link" @click="navigateTo('/settings?tab=media-scraping')">
              <div class="stat-row">
                <span class="stat-val" :class="statsLoading ? 'stat-num-loading' : 'stat-num-ready'">
                  {{ statsLoading ? '—' : animatedNums.imageCacheCount.toLocaleString() }}
                </span>
                <span class="stat-cache-size" v-if="!statsLoading && stats.imageCacheSize">{{ formattedCacheSize }}</span>
              </div>
              <span class="stat-lbl">图片缓存</span>
            </div>
          </div>
        </div>
      </div>
    </div>

        <!-- 近期活动侧边栏（与 Hero 平级，撑开时只挤压 hero-section） -->
        <div class="activity-sidebar" :class="{ 'activity-sidebar--open': activityVisible }">
          <div class="activity-sidebar-inner">
            <div class="activity-sidebar-hd">
              <span class="activity-sidebar-title">近期活动</span>
              <div class="activity-hd-actions">
                <el-button type="primary" link size="small" @click="navigateTo('/tasks')">查看全部</el-button>
                <div
                  class="activity-pin-btn"
                  :class="{ 'activity-pin-btn--active': activityPinned }"
                  :title="activityPinned ? '取消固定' : '固定面板'"
                  @click="togglePin"
                >
                  <el-icon><Lock v-if="activityPinned" /><Unlock v-else /></el-icon>
                </div>
                <el-button text circle size="small" @click="closeActivity">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </div>
            <div class="activity-list">
              <div v-for="activity in activities" :key="activity.id" class="act-item">
                <div class="act-icon" :style="{ backgroundColor: activity.color + '20', color: activity.color }">
                  <el-icon><Check v-if="activity.statusType === 'success'" /><Close v-else-if="activity.statusType === 'danger'" /><Loading v-else-if="activity.statusType === 'primary'" /><InfoFilled v-else /></el-icon>
                </div>
                <div class="act-content">
                  <div class="act-title" :title="activity.title">{{ activity.title }}</div>
                </div>
                <div class="act-time">{{ activity.time }}</div>
                <div class="act-status">
                  <el-tag size="small" :type="activity.statusType" effect="light">{{ activity.statusLabel }}</el-tag>
                </div>
              </div>
              <el-empty v-if="activities.length === 0" description="暂无活动记录" :image-size="60" />
            </div>
          </div>
        </div>
      </div>

      <div class="dashboard-content">
        <!-- 配置引导卡片（媒体行全空且加载完毕时显示） -->
        <div
          class="setup-guide-section"
          v-if="forceEmpty || (!watchHistoryLoading && !latestLoading && watchHistory.length === 0 && latestMovies.length === 0 && latestEpisodes.length === 0)"
        >
          <div class="setup-guide-card" @click="navigateTo('/media-servers')">
            <div class="sgc-icon">📺</div>
            <div class="sgc-body">
              <div class="sgc-title">连接媒体服务器</div>
              <div class="sgc-desc">接入 Jellyfin / Emby / Plex，首页将展示你的观看历史和最新入库内容</div>
            </div>
            <div class="sgc-arrow">→</div>
          </div>
          <div class="setup-guide-card" @click="navigateTo('/settings?tab=pt-sites')">
            <div class="sgc-icon">🔗</div>
            <div class="sgc-body">
              <div class="sgc-title">添加 PT 站点</div>
              <div class="sgc-desc">配置 MTeam 等站点，同步资源后 Hero 区域将展示精美海报轮播</div>
            </div>
            <div class="sgc-arrow">→</div>
          </div>
          <div class="setup-guide-card" @click="navigateTo('/subscriptions')">
            <div class="sgc-icon">📌</div>
            <div class="sgc-body">
              <div class="sgc-title">创建订阅</div>
              <div class="sgc-desc">订阅感兴趣的电视剧，新集自动识别并下载</div>
            </div>
            <div class="sgc-arrow">→</div>
          </div>
        </div>

        <!-- 2. 继续观看 -->
        <div class="media-row-section" v-if="watchHistoryLoading || watchHistory.length > 0">
          <div class="section-title">
            <span>继续观看</span>
            <el-button v-if="!watchHistoryLoading" type="primary" link @click="navigateTo('/media-servers?tab=history')">更多 <el-icon><ArrowRight /></el-icon></el-button>
          </div>
          <div class="scroll-row">
            <!-- 骨架：纯色占位 -->
            <template v-if="watchHistoryLoading">
              <div v-for="i in 5" :key="`wh-sk-${i}`" class="continue-card">
                <div class="card-img-wrapper"></div>
              </div>
            </template>
            <!-- 真实内容 -->
            <template v-else>
              <div v-for="item in watchHistory.slice(0, 10)" :key="item.id" class="continue-card" @click="openWatchHistoryItem(item)">
                <div class="card-img-wrapper">
                  <el-image :src="getMediaServerImageUrl(item.image_url, item.media_server_config_id)" fit="cover" lazy>
                     <template #error><div class="img-err"><el-icon><Picture /></el-icon></div></template>
                  </el-image>
                  <div class="card-overlay">
                    <el-icon class="play-icon"><VideoPlay /></el-icon>
                  </div>
                  <div class="card-hover-info">
                    <div class="hover-title">{{ item.title }}</div>
                    <div class="hover-meta">{{ formatRelativeTime(item.last_played_at) }}</div>
                  </div>
                  <div class="progress-bar-container">
                    <div class="progress-bar" :style="{ width: item.playback_progress + '%' }"></div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- 3. 最近添加 -->
        <div class="media-row-section" v-if="latestLoading || latestMovies.length > 0 || latestEpisodes.length > 0">
          <div class="section-title">
            <span>最近添加</span>
          </div>

          <!-- 3a. 电影行（纵向海报卡片 2:3） -->
          <div class="latest-sub-section" v-if="latestLoading || latestMovies.length > 0">
            <div class="sub-section-label">电影</div>
            <div class="scroll-row">
              <template v-if="latestLoading">
                <div v-for="i in 7" :key="`lm-sk-${i}`" class="poster-card">
                  <div class="card-img-wrapper"></div>
                </div>
              </template>
              <template v-else>
                <div v-for="item in latestMovies.slice(0, 15)" :key="item.Id" class="poster-card" @click="navigateToMedia(item)">
                  <div class="card-img-wrapper">
                    <el-image :src="getLatestMediaPoster(item)" fit="cover" lazy />
                    <div class="card-overlay">
                      <el-icon class="play-icon"><VideoPlay /></el-icon>
                    </div>
                    <div class="card-hover-info">
                      <div class="hover-title">{{ item.Name }}</div>
                      <div class="hover-meta">{{ formatRelativeTime(item.DateCreated) }}</div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- 3b. 剧集行（横向缩略图卡片 16:9） -->
          <div class="latest-sub-section" v-if="latestLoading || latestEpisodes.length > 0">
            <div class="sub-section-label">剧集</div>
            <div class="scroll-row">
              <template v-if="latestLoading">
                <div v-for="i in 7" :key="`le-sk-${i}`" class="episode-latest-card">
                  <div class="card-img-wrapper"></div>
                </div>
              </template>
              <template v-else>
                <div v-for="item in latestEpisodes.slice(0, 15)" :key="item.Id" class="episode-latest-card" @click="navigateToMedia(item)">
                  <div class="card-img-wrapper">
                    <el-image :src="getLatestMediaPoster(item)" fit="cover" lazy />
                    <div class="card-overlay">
                      <el-icon class="play-icon"><VideoPlay /></el-icon>
                    </div>
                    <div class="card-hover-info">
                      <div class="hover-title">{{ item.SeriesName || item.Name }}</div>
                      <div class="hover-episode" v-if="item.Type === 'Episode' && item.IndexNumber">
                        S{{ item.ParentIndexNumber || 1 }}-E{{ item.IndexNumber }} {{ item.Name }}
                      </div>
                      <div class="hover-meta">{{ formatRelativeTime(item.DateCreated) }}</div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>


  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Picture, VideoPlay, ArrowRight, Check, Close, Loading, InfoFilled, DataLine, Lock, Unlock
} from '@element-plus/icons-vue'
import api from '@/api'
import type { MediaBackdropItem } from '@/api/modules/dashboard'
import { formatFileSize, formatRelativeTime } from '@/utils/format'
import { getMediaServerImageUrl, getProxiedImageUrl } from '@/utils'
import { getServerBaseUrl } from '@/api/modules/mediaServer'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 开发用：URL 加 ?empty=1 强制显示空状态（方便测试引导页面）
const forceEmpty = import.meta.env.DEV && route.query.empty === '1'

// 数字滚动动画的展示值（从 0 滚动到目标值）
const animatedNums = ref({
  resources: 0,
  movies: 0,
  tvs: 0,
  actors: 0,
  subscriptions: 0,
  totalDownloads: 0,
  totalMediaItems: 0,
  sites: 0,
  imageCacheCount: 0,
})

// 触发数字从 0 滚动到目标值（700ms ease-out cubic）
const triggerCountUp = (targets: Partial<typeof animatedNums.value>) => {
  const duration = 700
  const startTime = performance.now()
  const startVals = { ...animatedNums.value }
  const step = (now: number) => {
    const progress = Math.min((now - startTime) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    const updated = { ...animatedNums.value }
    for (const key in targets) {
      const k = key as keyof typeof animatedNums.value
      updated[k] = Math.round((startVals[k] || 0) + ((targets[k] ?? 0) - (startVals[k] || 0)) * eased)
    }
    animatedNums.value = updated
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

// 总统计数据
const stats = ref({
  // 发现
  sites: 0,
  resources: 0,
  movies: 0,
  tvs: 0,
  actors: 0,
  // 媒体
  subscriptions: 0,
  totalDownloads: 0,
  activeDownloads: 0,
  storage: 0,
  mediaServerCount: 0,
  totalMediaItems: 0,
  // 系统
  imageCacheCount: 0,
  imageCacheSize: 0,
})

// 今日新增统计（用于绿色 badge）
const todayStats = ref({
  resources: 0,
  movies: 0,
  newTvs: 0,
  updatedTvs: 0,
  actors: 0,
  subscriptions: 0,
  downloads: 0,
})

const watchHistory = ref<any[]>([])
const latestMovies = ref<any[]>([])
const latestEpisodes = ref<any[]>([])

// Hero 轮播
const heroBackdrops = ref<MediaBackdropItem[]>([])
const currentHeroIndex = ref(0)
let carouselTimer: number | null = null

const currentHeroItem = computed(() => heroBackdrops.value[currentHeroIndex.value] || null)

// 检测 backdrop 宽高比，缓存结果避免重复加载
const backdropOrientationCache = new Map<string, boolean>() // url -> isPortrait
const backdropIsPortrait = ref(false)

const detectBackdropOrientation = (url: string) => {
  if (!url) { backdropIsPortrait.value = false; return }
  if (backdropOrientationCache.has(url)) {
    backdropIsPortrait.value = backdropOrientationCache.get(url)!
    return
  }
  const img = new Image()
  img.onload = () => {
    const isPortrait = img.naturalHeight > img.naturalWidth
    backdropOrientationCache.set(url, isPortrait)
    backdropIsPortrait.value = isPortrait
  }
  img.onerror = () => {
    backdropOrientationCache.set(url, false)
    backdropIsPortrait.value = false
  }
  img.src = url
}

// 每次切换 hero 条目时检测新 backdrop
watch(currentHeroItem, (item) => {
  const url = item?.backdrop_url ? getProxiedImageUrl(item.backdrop_url) : ''
  detectBackdropOrientation(url)
}, { immediate: true })

const heroBgStyle = computed(() => {
  const item = currentHeroItem.value
  if (!item?.backdrop_url) return {}
  const isPortrait = backdropIsPortrait.value
  return {
    backgroundImage: `url('${getProxiedImageUrl(item.backdrop_url)}')`,
    backgroundSize: isPortrait ? 'contain' : 'cover',
    backgroundPosition: isPortrait ? 'center center' : 'center 20%',
    backgroundRepeat: 'no-repeat',
  }
})

const heroBgBlurStyle = computed(() => {
  const item = currentHeroItem.value
  if (!item?.poster_url) return {}
  return {
    backgroundImage: `url('${getProxiedImageUrl(item.poster_url)}')`,
    backgroundSize: 'cover',
    backgroundPosition: 'center center',
  }
})

const startCarousel = () => {
  if (heroBackdrops.value.length <= 1) return
  stopCarousel()
  carouselTimer = window.setInterval(() => {
    currentHeroIndex.value = (currentHeroIndex.value + 1) % heroBackdrops.value.length
  }, 6000)
}
const stopCarousel = () => {
  if (carouselTimer !== null) { clearInterval(carouselTimer); carouselTimer = null }
}
const pauseCarousel = () => stopCarousel()
const resumeCarousel = () => startCarousel()
const jumpToSlide = (i: number) => { currentHeroIndex.value = i; stopCarousel(); startCarousel() }

const navigateToHeroItem = () => {
  const item = currentHeroItem.value
  if (!item) return
  const path = item.media_type === 'movie' ? `/movies/${item.id}` : `/tv/${item.id}`
  navigateTo(path)
}

onUnmounted(() => stopCarousel())

const formattedStorage = computed(() => formatFileSize(stats.value.storage))
const formattedCacheSize = computed(() => formatFileSize(stats.value.imageCacheSize))

interface ActivityItem {
  id: number
  title: string
  description?: string
  time: string
  color: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  statusLabel?: string
  statusType?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
}

// 各区块独立加载状态
const heroLoading = ref(true)       // 海报 + backdrop 轮播区
const statsLoading = ref(true)      // 右侧统计数字面板
const watchHistoryLoading = ref(true)
const latestLoading = ref(true)

const activities = ref<ActivityItem[]>([])
const initialPinned = localStorage.getItem('nf-activity-pinned') === 'true'
const activityVisible = ref(initialPinned)
const activityPinned = ref(initialPinned)

const togglePin = () => {
  activityPinned.value = !activityPinned.value
  localStorage.setItem('nf-activity-pinned', String(activityPinned.value))
}

const closeActivity = () => {
  activityVisible.value = false
  if (activityPinned.value) {
    activityPinned.value = false
    localStorage.setItem('nf-activity-pinned', 'false')
  }
}


const getStatusConfig = (status: string) => {
  switch (status) {
    case 'completed':
    case 'success':
      return { color: '#10b981', type: 'success', label: '完成' }
    case 'failed':
    case 'error':
      return { color: '#ef4444', type: 'danger', label: '失败' }
    case 'running':
    case 'downloading':
    case 'seeding':
    case 'identifying':
    case 'scanning':
      return { color: '#3b82f6', type: 'primary', label: '进行中' }
    case 'pending':
    case 'queued':
      return { color: '#f59e0b', type: 'warning', label: '等待' }
    default:
      return { color: '#9ca3af', type: 'info', label: status || '未知' }
  }
}

// ── 各区块独立 fetch，并行发出不互相阻塞 ────────────────────────────────

const fetchBackdrops = async () => {
  try {
    const res = await api.dashboard.getDashboardBackdrops()
    const data = res.data || res
    if (data.recent_media_backdrops?.length > 0) {
      heroBackdrops.value = data.recent_media_backdrops
      currentHeroIndex.value = 0
      startCarousel()
    }
  } catch (error) {
    console.warn('[dashboard] fetchBackdrops failed:', error)
  } finally {
    heroLoading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await api.dashboard.getDashboardStats()
    const data = res.data || res

    stats.value = {
      sites: data.total_sites || 0,
      resources: data.total_resources || 0,
      movies: data.total_movies || 0,
      tvs: data.total_tvs || 0,
      actors: data.total_actors || 0,
      subscriptions: data.total_subscriptions || 0,
      totalDownloads: data.total_downloads || 0,
      activeDownloads: data.active_downloads || 0,
      storage: data.total_storage_used || 0,
      mediaServerCount: data.media_server_count || 0,
      totalMediaItems: data.total_media_items || 0,
      imageCacheCount: data.image_cache_count || 0,
      imageCacheSize: data.image_cache_size || 0,
    }

    todayStats.value = {
      resources: data.today_new_resources || 0,
      movies: data.today_new_movies || 0,
      newTvs: data.today_new_tvs || 0,
      updatedTvs: data.today_updated_tvs || 0,
      actors: data.today_new_actors || 0,
      subscriptions: data.today_new_subscriptions || 0,
      downloads: data.today_new_downloads || 0,
    }
    // 触发数字滚动动画
    triggerCountUp({
      resources: stats.value.resources,
      movies: stats.value.movies,
      tvs: stats.value.tvs,
      actors: stats.value.actors,
      subscriptions: stats.value.subscriptions,
      totalDownloads: stats.value.totalDownloads,
      totalMediaItems: stats.value.totalMediaItems,
      sites: stats.value.sites,
      imageCacheCount: stats.value.imageCacheCount,
    })
  } catch (error) {
    console.error('[dashboard] fetchStats failed:', error)
  } finally {
    statsLoading.value = false
  }
}

const fetchWatchHistory = async () => {
  try {
    const res = await api.dashboard.getDashboardWatchHistory()
    const data = res.data || res
    watchHistory.value = data.watch_history || []
  } catch (error) {
    console.warn('[dashboard] fetchWatchHistory failed:', error)
  } finally {
    watchHistoryLoading.value = false
  }
}

const fetchLatestMedia = async () => {
  try {
    const configsRes = await api.mediaServer.getMediaServerConfigs().catch(() => ({ data: [] }))
    const configs = configsRes.data || configsRes || []

    if (configs.length === 0) { latestLoading.value = false; return }

    const mergeAndSort = (results: any[], cfgs: any[]) => {
      const all = results.flatMap((res: any, i: number) => {
        const config = cfgs[i]
        const data = res.data || res || []
        if (!Array.isArray(data)) return []
        return data.map((item: any) => ({
          ...item,
          config_id: config.id,
          server_type: config.type,
          server_url: getServerBaseUrl(config),
          machine_id: config.server_config?.machineIdentifier || '',
        }))
      })
      all.sort((a, b) => {
        const ta = a.DateCreated ? new Date(a.DateCreated).getTime() : 0
        const tb = b.DateCreated ? new Date(b.DateCreated).getTime() : 0
        return tb - ta
      })
      return all
    }

    const [movieResults, episodeResults] = await Promise.all([
      Promise.all(configs.map((config: any) =>
        api.mediaServer.getMediaServerLatest(config.id, 20, 'Movie').catch((e: any) => {
          console.warn(`[dashboard] fetchLatestMovies config=${config.id} failed`, e)
          return { data: [] }
        })
      )),
      Promise.all(configs.map((config: any) =>
        api.mediaServer.getMediaServerLatest(config.id, 20, 'Episode').catch((e: any) => {
          console.warn(`[dashboard] fetchLatestEpisodes config=${config.id} failed`, e)
          return { data: [] }
        })
      )),
    ])

    latestMovies.value = mergeAndSort(movieResults, configs)
    latestEpisodes.value = mergeAndSort(episodeResults, configs)
  } catch (error) {
    console.warn('[dashboard] fetchLatestMedia failed:', error)
  } finally {
    latestLoading.value = false
  }
}

const fetchActivity = async () => {
  try {
    const res = await api.dashboard.getDashboardActivity()
    const data = res.data || res
    if (data.recent_activities) {
      activities.value = data.recent_activities.map(task => {
        const config = getStatusConfig(task.status)
        const time = task.updated_at || task.created_at || new Date().toISOString()
        return {
          id: task.id,
          title: task.task_name,
          time: formatRelativeTime(time),
          color: config.color,
          type: config.type as any,
          statusLabel: config.label,
          statusType: config.type as any,
        }
      })
    }
  } catch (e) {
    console.warn('[dashboard] fetchActivity failed:', e)
  }
}

// 五路并行，互不阻塞
const fetchData = () => {
  fetchBackdrops()      // 最快：2 个 DB 查询 → Hero 轮播立即可见
  fetchStats()          // 快：计数 SQL + media_items DB 缓存 → 右侧数字面板
  fetchWatchHistory()   // 慢：调 Jellyfin API → 继续观看区
  fetchLatestMedia()    // 慢：调 Jellyfin API → 最近添加区
  fetchActivity()       // 快：DB 查询 → 近期活动侧边栏
}

const getLatestMediaPoster = (item: any) => {
  if (!item) return ''
  const configId = item.config_id
  if (item.thumb && !item.ImageTags) {
    return getMediaServerImageUrl(item.thumb, configId)
  }
  return getMediaServerImageUrl(`/Items/${item.Id}/Images/Primary`, configId)
}

const getPlaybackUrl = (item: any) => {
  if (!item || !item.server_url) return ''
  const itemId = item.Id || item.ratingKey
  if (!itemId) return ''
  if (item.server_type === 'plex') {
    return `${item.server_url}/web/index.html#!/server/${item.machine_id}/details?key=%2Flibrary%2Fmetadata%2F${itemId}`
  }
  return `${item.server_url}/web/index.html#!/details?id=${itemId}`
}

const navigateToMedia = (item: any) => {
  const url = getPlaybackUrl(item)
  if (url) window.open(url, '_blank')
}

const openWatchHistoryItem = (item: any) => {
  if (item.playback_url) {
    window.open(item.playback_url, '_blank')
  } else {
    navigateTo('/media-servers?tab=history')
  }
}

onMounted(() => {
  fetchData()
})

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<style scoped>
.dashboard-container {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  padding-bottom: 2rem;
  /* 抵消上层可能的 padding */
  margin-top: -10px;
}

/* ========== 1. 首行布局 ========== */
.dashboard-top-row {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  width: 100%;
  margin-bottom: 10px;
}

/* ========== 1. Hero 左/中/右三列 ========== */
.hero-section {
  display: grid;
  grid-template-columns: 200px 50fr 37fr; /* 左侧固定，中右按原比例分配 */
  height: 340px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--nf-shadow-md);
  border: 1px solid var(--nf-border-base);
  flex: 1;
  min-width: 0;
}

/* 左：Backdrop 图区 */
.hero-left {
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.hero-left:hover .hero-bg-layers {
  transform: scale(1.04);
}

/* 包裹两层的容器 */
.hero-bg-layers {
  position: absolute;
  inset: 0;
  z-index: 0;
  transition: transform 0.6s ease;
}

/* 底层：模糊 Poster，inset 向外扩展避免 blur 白边 */
.hero-bg-blur {
  position: absolute;
  inset: -40px;
  background-size: cover;
  background-position: center center;
  filter: blur(28px) brightness(0.55) saturate(1.4);
  z-index: 0;
}

/* 上层：Backdrop */
.hero-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center 20%;
  z-index: 1;
}

/* 纵图时：边缘渐隐，四周淡出融入底层模糊 poster */
.hero-bg--portrait {
  -webkit-mask-image: radial-gradient(ellipse 38% 95% at center, black 40%, transparent 78%);
  mask-image: radial-gradient(ellipse 38% 95% at center, black 40%, transparent 78%);
}

/* 淡入淡出过渡 */
.hero-bg-fade-enter-active {
  transition: opacity 0.9s ease;
  z-index: 1;
}
.hero-bg-fade-leave-active {
  transition: opacity 0.9s ease;
  z-index: 2;
}
.hero-bg-fade-enter-from,
.hero-bg-fade-leave-to {
  opacity: 0;
}

/* 两侧过渡：左侧从海报衔接，右侧渐变到统计面板背景 */
.hero-left-edge {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to right,
    rgba(0,0,0,0.18) 0%,
    transparent 12%,
    transparent 82%,
    var(--nf-bg-elevated) 100%
  );
  z-index: 3;
  pointer-events: none;
}

/* 底部信息覆盖层 */
.hero-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 4;
  padding: 48px 20px 36px;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.55) 40%, rgba(0,0,0,0.82) 100%);
}

.hero-info-overview {
  font-size: 13px;
  color: rgba(255,255,255,0.88);
  text-shadow: 0 1px 4px rgba(0,0,0,0.8);
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  letter-spacing: 0.01em;
}

.hero-info-fade-enter-active {
  transition: opacity 0.6s ease 0.2s;
}
.hero-info-fade-leave-active {
  transition: opacity 0.3s ease;
}
.hero-info-fade-enter-from,
.hero-info-fade-leave-to {
  opacity: 0;
}

/* 轮播指示点 */
.hero-dots {
  position: absolute;
  bottom: 16px;
  left: 20px;
  z-index: 4;
  display: flex;
  gap: 6px;
  align-items: center;
}

.hero-dot {
  width: 6px;
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-dot.active {
  width: 22px;
  background: rgba(255, 255, 255, 0.95);
}

.hero-dot:hover:not(.active) {
  background: rgba(255, 255, 255, 0.65);
}

/* ── 骨架 shimmer 动画（统一光线滑过效果）── */
@keyframes sk-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.hero-img-placeholder,
.card-img-wrapper:empty,
.card-sk-line {
  background: linear-gradient(
    90deg,
    var(--nf-bg-container) 25%,
    var(--nf-bg-overlay)   50%,
    var(--nf-bg-container) 75%
  );
  background-size: 200% 100%;
  animation: sk-shimmer 2.5s infinite ease-in-out;
}

/* hero 骨架需要撑满容器 */
.hero-img-placeholder {
  width: 100%;
  height: 100%;
}

/* 中：海报列 */
.hero-poster {
  position: relative;
  overflow: hidden;
  cursor: pointer;
  background: var(--nf-bg-overlay);
}

.hero-poster :deep(.el-image) {
  width: 100%;
  height: 100%;
  transition: transform 0.6s ease;
}

.hero-poster:hover :deep(.el-image) {
  transform: scale(1.05);
}

.poster-col-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--nf-text-placeholder);
}

/* 海报底部渐变 + 信息覆盖层 */
.hero-poster-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 48px 12px 14px;
  background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.55) 55%, transparent 100%);
  z-index: 2;
  pointer-events: none;
}

.poster-ov-badges {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 5px;
  flex-wrap: wrap;
}

.poster-ov-type {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(255,255,255,0.18);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.3);
  backdrop-filter: blur(4px);
  letter-spacing: 0.5px;
}

.poster-ov-rating {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
}

.poster-ov-title {
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-shadow: 0 1px 4px rgba(0,0,0,0.5);
}

.poster-ov-year {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  margin-top: 4px;
}

/* 右：指标面板 */
.hero-right {
  position: relative;
  background: var(--nf-bg-elevated);
  padding: 16px 18px 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

/* 指标分组 */
.stat-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
  flex: 1;
  min-height: 0;
}

.stat-group-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--nf-text-placeholder);
  text-transform: uppercase;
  letter-spacing: 1px;
  line-height: 1;
}

.stat-group-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0 4px;
  align-items: start;
}

.stat-group-divider {
  height: 1px;
  background: var(--nf-border-base);
  margin: 6px 0;
  flex-shrink: 0;
}

/* 单个指标项 */
.hero-stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

/* 可点击指标项 */
.hero-stat-link {
  cursor: pointer;
  border-radius: 6px;
  padding: 3px 4px;
  margin: -3px -4px;
  transition: background 0.18s;
}
.hero-stat-link:hover {
  background: rgba(var(--el-color-primary-rgb), 0.07);
}
.hero-stat-link:hover .stat-val {
  color: var(--el-color-primary);
}

.stat-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex-wrap: wrap;
}

.stat-val {
  font-size: 16px;
  font-weight: 800;
  color: var(--nf-text-primary);
  line-height: 1;
  letter-spacing: -0.4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* 统计数字：加载中占位（闪烁破折号） */
.stat-num-loading {
  color: var(--nf-text-placeholder) !important;
  animation: stat-blink 1.8s ease-in-out infinite;
}

@keyframes stat-blink {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 0.75; }
}

/* 统计数字：加载完成（从下方淡入 + 弹性回弹） */
.stat-num-ready {
  display: inline-block;
  animation: stat-rise 0.5s cubic-bezier(0.34, 1.4, 0.64, 1) both;
}

@keyframes stat-rise {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 今日增量绿色小徽章 */
.stat-badge {
  font-size: 10px;
  font-weight: 700;
  color: var(--el-color-success);
  background: rgba(var(--el-color-success-rgb), 0.12);
  padding: 1px 4px;
  border-radius: 4px;
  line-height: 1.6;
  white-space: nowrap;
}

/* 图片缓存大小副标 */
.stat-cache-size {
  font-size: 10px;
  color: var(--nf-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.stat-lbl {
  font-size: 11px;
  color: var(--nf-text-placeholder);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ========== 主体布局 ========== */
.dashboard-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow-x: clip; /* 防止内容水平溢出到侧边栏区域 */
}

.dashboard-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ========== 横向滚动媒体栏 ========== */
.media-row-section {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 20px;
  font-weight: 700;
  color: var(--nf-text-primary);
  padding: 0 8px;
}

.scroll-row {
  min-width: 0;
  display: flex;
  gap: 20px;
  overflow-x: auto;
  padding-bottom: 20px;
  margin-bottom: -20px;
  scrollbar-width: none;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  padding-left: 8px;
}

.scroll-row::-webkit-scrollbar {
  display: none;
}

/* 末尾留白：比 padding-right 在所有浏览器下更可靠 */
.scroll-row::after {
  content: '';
  flex: 0 0 8px;
}

/* 继续观看长卡片 (16:9) */
.continue-card {
  flex: 0 0 280px;
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.3s ease;
}

.continue-card:hover {
  transform: translateY(-6px);
}

.continue-card:hover .card-overlay {
  opacity: 1;
}

.continue-card:hover .play-icon {
  transform: scale(1);
}

.continue-card .card-img-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 12px;
  overflow: hidden;
  background-color: var(--nf-bg-overlay);
  box-shadow: var(--nf-shadow-sm);
  margin-bottom: 12px;
}

.card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 2;
}

.play-icon {
  font-size: 54px;
  color: #fff;
  transform: scale(0.85);
  transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.4));
}

.progress-bar-container {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: rgba(255, 255, 255, 0.25);
  z-index: 3;
}

.progress-bar {
  height: 100%;
  background: var(--el-color-danger);
  border-radius: 0 2px 2px 0;
}

/* 最近添加竖卡片 (2:3) */
.poster-card {
  flex: 0 0 160px;
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.3s ease;
}

.poster-card:hover {
  transform: translateY(-6px);
}

.poster-card:hover .card-overlay {
  opacity: 1;
}

.poster-card:hover .play-icon {
  transform: scale(1);
}

.poster-card .card-img-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 2/3;
  border-radius: 12px;
  overflow: hidden;
  background-color: var(--nf-bg-overlay);
  box-shadow: var(--nf-shadow-sm);
  margin-bottom: 12px;
}

.tag-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  z-index: 2;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.1);
}


.card-img-wrapper .el-image {
  width: 100%;
  height: 100%;
  transition: transform 0.6s ease;
}

.continue-card:hover .card-img-wrapper .el-image,
.poster-card:hover .card-img-wrapper .el-image {
  transform: scale(1.08);
}

.img-err {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--nf-text-placeholder);
}

/* 骨架文字占位线（替代 el-skeleton-item variant="p"） */
.card-sk-line {
  height: 10px;
  border-radius: 5px;
  /* shimmer 已在上方统一规则中定义 */
}

.card-info {
  padding: 0 6px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--nf-text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  word-break: break-all;
}

.card-meta {
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin-top: 6px;
}

/* ========== 悬浮信息覆盖层 ========== */
.card-hover-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 36px 10px 10px;
  background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.5) 55%, transparent 100%);
  z-index: 3;
  opacity: 1;
  transform: translateY(0);
  pointer-events: none;
}

.hover-title {
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0,0,0,0.6);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.35;
}

.hover-episode {
  font-size: 11px;
  color: rgba(255,255,255,0.75);
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hover-meta {
  font-size: 11px;
  color: rgba(255,255,255,0.55);
  margin-top: 3px;
}

/* ========== 最近添加：子分类布局 ========== */
.latest-sub-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sub-section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--nf-text-secondary);
  padding: 0 8px;
}

/* 剧集横向卡片 (16:9) */
.episode-latest-card {
  flex: 0 0 240px;
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.3s ease;
}

.episode-latest-card:hover {
  transform: translateY(-6px);
}

.episode-latest-card:hover .card-overlay {
  opacity: 1;
}

.episode-latest-card:hover .play-icon {
  transform: scale(1);
}

.episode-latest-card .card-img-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 12px;
  overflow: hidden;
  background-color: var(--nf-bg-overlay);
  box-shadow: var(--nf-shadow-sm);
}

.episode-latest-card:hover .card-img-wrapper .el-image {
  transform: scale(1.08);
}

/* ========== 近期活动侧边栏 ========== */
.activity-sidebar {
  width: 0;
  overflow: hidden;
  flex-shrink: 0;
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.activity-sidebar--open {
  width: 380px;
}

.activity-sidebar-inner {
  width: 360px;
  height: 340px;
  margin-left: 20px;
  background: var(--nf-bg-elevated);
  border: 1px solid var(--nf-border-base);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.activity-sidebar-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--nf-border-base);
  flex-shrink: 0;
}

.activity-sidebar-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--nf-text-primary);
}

.activity-hd-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.act-item {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  border-bottom: 1px solid var(--nf-border-base);
  transition: background 0.2s;
}

.act-item:last-child {
  border-bottom: none;
}

.act-item:hover {
  background: var(--nf-bg-overlay);
}

.act-icon {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}

.act-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  min-width: 0;
}

.act-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--nf-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.act-desc {
  font-size: 10px;
  color: var(--nf-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.act-time {
  font-size: 10px;
  color: var(--nf-text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ========== 近期活动切换按钮（hero-right 右上角）========== */
.activity-toggle-btn {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: none;
  background: rgba(255, 255, 255, 0.07);
  color: var(--nf-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s, color 0.2s;
  z-index: 5;
}

.activity-toggle-btn:hover {
  background: rgba(var(--el-color-primary-rgb), 0.14);
  color: var(--el-color-primary);
}



/* 固定按钮 */
.activity-pin-btn {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
  color: var(--nf-text-secondary);
  transition: background 0.2s, color 0.2s;
  flex-shrink: 0;
}

.activity-pin-btn:hover {
  background: rgba(var(--el-color-primary-rgb), 0.1);
  color: var(--el-color-primary);
}

.activity-pin-btn--active {
  color: var(--el-color-primary);
}

/* ========== 欢迎引导（Hero 中间空状态） ========== */
.hero-left--welcome {
  cursor: default;
  background: linear-gradient(135deg, var(--nf-bg-elevated) 0%, var(--nf-bg-overlay) 100%);
}

.welcome-pane {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 28px 36px;
  z-index: 2;
}

.welcome-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.welcome-logo {
  font-size: 28px;
  line-height: 1;
}

.welcome-app-name {
  font-size: 22px;
  font-weight: 800;
  color: var(--nf-text-primary);
  letter-spacing: -0.5px;
}

.welcome-tagline {
  font-size: 13px;
  color: var(--nf-text-secondary);
  margin: 0 0 20px;
}

.setup-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setup-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--nf-border-base);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
}

.setup-step:hover {
  background: rgba(var(--el-color-primary-rgb), 0.08);
  border-color: rgba(var(--el-color-primary-rgb), 0.3);
  transform: translateX(3px);
}

.setup-step--done {
  border-color: rgba(var(--el-color-success-rgb), 0.4);
  background: rgba(var(--el-color-success-rgb), 0.06);
}

.setup-step--done .step-circle {
  background: var(--el-color-success);
  color: #fff;
  border-color: var(--el-color-success);
}

.step-circle {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--nf-border-base);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--nf-text-secondary);
  flex-shrink: 0;
  transition: all 0.2s;
}

.step-body {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--nf-text-primary);
  line-height: 1.3;
}

.step-desc {
  font-size: 11px;
  color: var(--nf-text-secondary);
  margin-top: 1px;
}

.step-arrow {
  font-size: 14px;
  color: var(--nf-text-placeholder);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.setup-step:hover .step-arrow {
  transform: translateX(3px);
  color: var(--el-color-primary);
}

/* ========== 媒体行空状态引导卡片 ========== */
.setup-guide-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 8px 8px 0;
}

.setup-guide-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 14px;
  background: var(--nf-bg-elevated);
  border: 1px solid var(--nf-border-base);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}

.setup-guide-card:hover {
  background: var(--nf-bg-overlay);
  border-color: rgba(var(--el-color-primary-rgb), 0.35);
  transform: translateY(-2px);
  box-shadow: var(--nf-shadow-sm);
}

.sgc-icon {
  font-size: 28px;
  flex-shrink: 0;
  line-height: 1;
}

.sgc-body {
  flex: 1;
  min-width: 0;
}

.sgc-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--nf-text-primary);
}

.sgc-desc {
  font-size: 13px;
  color: var(--nf-text-secondary);
  margin-top: 3px;
  line-height: 1.5;
}

.sgc-arrow {
  font-size: 18px;
  color: var(--nf-text-placeholder);
  flex-shrink: 0;
  transition: transform 0.2s, color 0.2s;
}

.setup-guide-card:hover .sgc-arrow {
  transform: translateX(4px);
  color: var(--el-color-primary);
}

/* 响应式 */
@media (max-width: 1200px) {
  .activity-sidebar--open {
    width: 300px;
  }
  .activity-sidebar-inner {
    width: 280px;
  }
}

@media (max-width: 768px) {
  .welcome-pane {
    padding: 20px 20px;
  }
  .welcome-app-name {
    font-size: 18px;
  }
  .setup-steps {
    gap: 6px;
  }
  .setup-step {
    padding: 8px 12px;
  }

  .hero-section {
    grid-template-columns: 1fr;
    grid-template-rows: 160px auto;
    height: auto;
    margin-bottom: 24px;
  }

  /* 移动端隐藏海报列 */
  .hero-poster {
    display: none;
  }

  /* 移动端 backdrop 不需要向右渐变，改为简单底部遮罩 */
  .hero-left-edge {
    background: linear-gradient(to bottom, transparent 50%, rgba(0,0,0,0.25) 100%);
  }

  /* 移动端 160px 不够展示简介文字，隐藏避免与轮播点重叠 */
  .hero-info {
    display: none;
  }

  /* 轮播点移到更低位置，避免与遮罩重叠 */
  .hero-dots {
    bottom: 8px;
  }

  .hero-right {
    padding: 16px 16px 20px;
    justify-content: flex-start;
    gap: 10px;
  }

  /* 移动端高度 auto，flex: 1 会导致内容溢出覆盖分割线 */
  .stat-group {
    flex: none;
    min-height: auto;
  }

  .stat-group-divider {
    margin: 0;
    flex-shrink: 0;
  }

  .stat-group-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px 8px;
  }

  .activity-toggle-btn {
    display: none;
  }
}
</style>
