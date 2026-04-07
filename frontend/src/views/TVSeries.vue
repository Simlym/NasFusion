<template>
  <div class="page-container">
    <!-- 回到顶部 -->
    <el-backtop target=".el-main" :right="40" :bottom="40" />


    <!-- 筛选面板（含工具栏） -->
    <div class="filter-panel">
      <!-- 顶部工具栏行 -->
      <div class="filter-header">
        <div class="header-left">
          <span class="total-count">共 {{ pagination.total }} 部剧集</span>
          <button class="mobile-filter-toggle" @click="filterExpanded = !filterExpanded">
            <el-icon><Filter /></el-icon>
            筛选
            <span v-if="activeFilterCount > 0" class="mobile-filter-badge">{{ activeFilterCount }}</span>
            <el-icon class="filter-toggle-arrow" :class="{ 'is-expanded': filterExpanded }"><ArrowDown /></el-icon>
          </button>
        </div>
        <div class="header-right">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索剧集..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
        </div>
      </div>
      <div class="filter-rows-wrapper" :class="{ 'is-expanded': filterExpanded }">
      <!-- 排序行 -->
      <div class="filter-row">
        <div class="filter-label">排序</div>
        <div class="filter-options">
          <div
            v-for="option in sortOptions"
            :key="option.value"
            class="filter-tag"
            :class="{ active: filters.sortBy === option.value }"
            @click="handleSortChange(option.value)"
          >
            {{ option.label }}
            <el-icon v-if="filters.sortBy === option.value" class="sort-icon">
              <Sort v-if="filters.order === 'desc'" />
              <SortUp v-else />
            </el-icon>
          </div>
        </div>
      </div>

      <!-- 榜单行 -->
      <div class="filter-row">
        <div class="filter-label">榜单</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: !filters.trendingCollection }"
            @click="handleTrendingCollectionChange('')"
          >
            全部
          </div>
          <div
            v-for="col in trendingCollections"
            :key="col.value"
            class="filter-tag"
            :class="{ active: filters.trendingCollection === col.value }"
            @click="handleTrendingCollectionChange(col.value)"
          >
            {{ col.label }}
          </div>
        </div>
      </div>

      <!-- 类型行 -->
      <div class="filter-row">
        <div class="filter-label">类型</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: !filters.genre }"
            @click="handleGenreChange('')"
          >
            全部
          </div>
          <div
            v-for="genre in genreOptions"
            :key="genre"
            class="filter-tag"
            :class="{ active: filters.genre === genre }"
            @click="handleGenreChange(genre)"
          >
            {{ genre }}
          </div>
        </div>
      </div>

      <!-- 状态行 -->
      <div class="filter-row">
        <div class="filter-label">状态</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: !filters.status }"
            @click="handleStatusChange(undefined)"
          >
            全部
          </div>
          <div
            v-for="status in statusOptions"
            :key="status.value"
            class="filter-tag"
            :class="{ active: filters.status === status.value }"
            @click="handleStatusChange(status.value)"
          >
            {{ status.label }}
          </div>
        </div>
      </div>

      <!-- 年份行 -->
      <div class="filter-row">
        <div class="filter-label">年份</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: !filters.year }"
            @click="handleYearChange(null)"
          >
            全部
          </div>
          <div
            v-for="year in yearOptions"
            :key="year"
            class="filter-tag"
            :class="{ active: filters.year && filters.year.getFullYear() === year }"
            @click="handleYearQuickChange(year)"
          >
            {{ year }}
          </div>
          <el-date-picker
            v-model="filters.year"
            type="year"
            placeholder="更多"
            :disabled-date="(date: Date) => date.getFullYear() > new Date().getFullYear()"
            style="width: 100px; margin-left: 8px;"
            size="small"
            @change="handleFilterChange"
          />
        </div>
      </div>

      <!-- 地区行 -->
      <div class="filter-row">
        <div class="filter-label">地区</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: !filters.country }"
            @click="handleCountryChange('')"
          >
            全部
          </div>
          <div
            v-for="country in countryOptions"
            :key="country"
            class="filter-tag"
            :class="{ active: filters.country === country }"
            @click="handleCountryChange(country)"
          >
            {{ country }}
          </div>
        </div>
      </div>

      <!-- 评分为行 -->
      <div class="filter-row">
        <div class="filter-label">评分</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: !filters.minRating }"
            @click="handleRatingChange(undefined)"
          >
            全部
          </div>
          <div
            v-for="rating in ratingOptions"
            :key="rating.value"
            class="filter-tag"
            :class="{ active: filters.minRating === rating.value }"
            @click="handleRatingChange(rating.value)"
          >
            {{ rating.label }}
          </div>
        </div>
      </div>

      <!-- 本地文件行 -->
      <div class="filter-row">
        <div class="filter-label">本地</div>
        <div class="filter-options">
          <div
            class="filter-tag"
            :class="{ active: filters.hasLocal === undefined }"
            @click="handleLocalChange(undefined)"
          >
            全部
          </div>
          <div
            class="filter-tag"
            :class="{ active: filters.hasLocal === true }"
            @click="handleLocalChange(true)"
          >
            已有本地
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 剧集卡片列表 -->
    <div v-loading="loading && tvSeries.length === 0" class="tv-grid">
      <el-card
v-for="tv in tvSeries" :key="tv.id" class="tv-card" :body-style="{ padding: '0px' }"
        shadow="hover" @click="handleViewTV(tv.id)">
        <div class="tv-poster">
          <el-image
v-if="tv.posterUrl" :src="getProxiedImageUrl(tv.posterUrl)" fit="cover" lazy
            class="poster-image">
            <template #placeholder>
              <div class="image-loading" :style="getRandomAnimationDelay()">
                <div class="loading-shimmer"></div>
              </div>
            </template>
            <template #error>
              <div class="image-slot">
                <el-icon>
                  <Picture />
                </el-icon>
              </div>
            </template>
          </el-image>
          <div v-else class="image-slot">
            <el-icon>
              <Picture />
            </el-icon>
          </div>

          <!-- 评分标签 -->
          <div v-if="tv.ratingDouban || tv.ratingTmdb || tv.ratingImdb" class="rating-badge">
            <el-icon>
              <Star />
            </el-icon>
            {{ tv.ratingDouban || tv.ratingTmdb || tv.ratingImdb }}
          </div>

          <!-- 本地文件标识 -->
          <div v-if="tv.hasLocal" class="local-badge">
            本地
          </div>

          <!-- 状态标签 -->
          <div v-if="tv.status" class="status-badge" :class="getStatusClass(tv.status)">
            {{ getStatusText(tv.status) }}
          </div>
        </div>

        <div class="tv-info">
          <div class="tv-title" :title="tv.title">{{ tv.title }}</div>
          <div class="tv-meta">
            <span v-if="tv.year">{{ tv.year }}</span>
            <span v-if="tv.numberOfSeasons"> • {{ tv.numberOfSeasons }}季</span>
          </div>
          <div v-if="tv.genres && tv.genres.length" class="tv-genres">
            <el-tag v-for="genre in tv.genres.slice(0, 3)" :key="genre" size="small" effect="plain">
              {{ genre }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 加载更多指示器 -->
    <div v-if="loadingMore" class="loading-more">
      <el-icon class="is-loading">
        <Loading />
      </el-icon>
      <span>加载中...</span>
    </div>

    <!-- 已加载全部 -->
    <div v-if="noMore && tvSeries.length > 0" class="no-more">
      已加载全部内容
    </div>

    <!-- 无限滚动触发器 -->
    <div ref="scrollTrigger" class="scroll-trigger"></div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && tvSeries.length === 0" description="暂无剧集数据">
      <el-button type="primary" @click="$router.push('/resources')"> 去识别PT资源 </el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, onActivated, onDeactivated, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Picture, Star, Loading, Sort, SortUp, Filter, ArrowDown } from '@element-plus/icons-vue'
import api from '@/api'
import type { UnifiedTV } from '@/types'
import { getProxiedImageUrl } from '@/utils'
import { useSettingsStore } from '@/stores'
import { getCollectionTypes } from '@/api/modules/trending'
import type { TrendingCollectionType } from '@/api/modules/trending'

// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'TVSeriesView'
})

const router = useRouter()
const settingsStore = useSettingsStore()

// 状态
const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const searchKeyword = ref('')
const tvSeries = ref<UnifiedTV[]>([])
const scrollTrigger = ref<HTMLElement | null>(null)

// 滚动位置保存（用于从详情页返回时恢复）
const savedScrollPosition = ref(0)

// 榜单筛选
const trendingCollections = ref<TrendingCollectionType[]>([])

// 筛选条件
const filters = reactive({
  hasFreeResource: undefined as boolean | undefined,
  year: undefined as Date | undefined,
  genre: undefined as string | undefined,
  country: undefined as string | undefined,
  status: undefined as string | undefined,
  sortBy: 'created_at',
  order: 'desc',
  minRating: undefined as number | undefined,
  trendingCollection: undefined as string | undefined,
  hasLocal: undefined as boolean | undefined
})

// 选项配置
const sortOptions = [
  { label: '最新添加', value: 'created_at' },
  { label: '最高评分', value: 'rating' },
  { label: '发行年份', value: 'year' },
  { label: '名称', value: 'title' }
]

const genreOptions = [
  '动作', '喜剧', '爱情', '科幻', '悬疑', '恐怖', '犯罪', '剧情', 
  '战争', '奇幻', '冒险', '动画', '纪录片', '惊悚', '家庭', '古装'
]

const countryOptions = [
  '中国大陆', '美国', '香港', '台湾', '日本', '韩国', '英国', '法国', '德国', '其他'
]

const statusOptions = [
  { label: '连载中', value: 'Returning Series' },
  { label: '已完结', value: 'Ended' },
  { label: '制作中', value: 'In Production' },
  { label: '已取消', value: 'Canceled' }
]

const yearOptions = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019]

const ratingOptions = [
  { label: '9分以上', value: 9 },
  { label: '8分以上', value: 8 },
  { label: '7分以上', value: 7 },
  { label: '6分以上', value: 6 },
  { label: '5分以上', value: 5 }
]

// 移动端筛选展开状态
const filterExpanded = ref(window.innerWidth > 768)
const activeFilterCount = computed(() => {
  let count = 0
  if (filters.trendingCollection) count++
  if (filters.genre) count++
  if (filters.status) count++
  if (filters.year) count++
  if (filters.country) count++
  if (filters.minRating) count++
  if (searchKeyword.value) count++
  if (filters.hasLocal !== undefined) count++
  return count
})
const handleMobileResize = () => {
  if (window.innerWidth > 768) filterExpanded.value = true
}

// 处理排序变化
const handleSortChange = (value: string) => {
  if (filters.sortBy === value) {
    // 切换排序方向
    filters.order = filters.order === 'desc' ? 'asc' : 'desc'
  } else {
    filters.sortBy = value
    filters.order = 'desc' // 默认降序
  }
  handleFilterChange()
}

// 处理类型变化
const handleGenreChange = (genre: string) => {
  filters.genre = genre || undefined
  handleFilterChange()
}

// 处理状态变化
const handleStatusChange = (status: string | undefined) => {
  filters.status = status
  handleFilterChange()
}

// 处理地区变化
const handleCountryChange = (country: string) => {
  filters.country = country || undefined
  handleFilterChange()
}

// 处理年份快速变化
const handleYearQuickChange = (year: number) => {
  if (filters.year && filters.year.getFullYear() === year) {
    filters.year = undefined // 取消选择
  } else {
    filters.year = new Date(year, 0, 1)
  }
  handleFilterChange()
}

const handleYearChange = (val: Date | null) => {
  filters.year = val || undefined
  handleFilterChange()
}

// 处理评分变化
const handleRatingChange = (rating: number | undefined) => {
  filters.minRating = rating
  handleFilterChange()
}

// 处理本地文件筛选变化
const handleLocalChange = (value: boolean | undefined) => {
  filters.hasLocal = value
  handleFilterChange()
}

// 加载榜单类型
const loadTrendingCollections = async () => {
  try {
    const res = await getCollectionTypes()
    if (res?.data?.types) {
      // 只显示剧集榜单（使用 mediaType 字段精确过滤）
      trendingCollections.value = res.data.types.filter((t: TrendingCollectionType) => t.mediaType === 'tv')
    }
  } catch (error) {
    console.error('Failed to load trending collections:', error)
  }
}

// 处理榜单筛选变化
// 处理榜单筛选变化
const handleTrendingCollectionChange = (collectionType: string) => {
  filters.trendingCollection = collectionType || undefined
  handleFilterChange()
}

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 加载剧集列表
const loadTVSeries = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const response = await api.tv.getTVList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      search: searchKeyword.value || undefined,
      hasFreeResource: filters.hasFreeResource,
      year: filters.year ? filters.year.getFullYear() : undefined,
      genre: filters.genre || undefined,
      excludeGenre: !settingsStore.tvShowAnime && filters.genre !== '动画' ? '动画' : undefined,
      country: filters.country || undefined,
      status: filters.status || undefined,
      sortBy: filters.sortBy,
      order: filters.order,
      minRating: filters.minRating,
      trendingCollection: filters.trendingCollection,
      hasLocal: filters.hasLocal
    })

    if (response?.data) {
      const newTVSeries = response.data.items || []

      if (append) {
        tvSeries.value = [...tvSeries.value, ...newTVSeries]
      } else {
        tvSeries.value = newTVSeries
      }

      pagination.total = response.data.total || 0

      // 检查是否已加载全部
      noMore.value = tvSeries.value.length >= pagination.total
    }
  } catch (error) {
    console.error('Failed to load TV series:', error)
    ElMessage.error('加载剧集列表失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  pagination.page = 1
  noMore.value = false
  loadTVSeries(false)
}

// 处理筛选变化
const handleFilterChange = () => {
  pagination.page = 1
  noMore.value = false
  loadTVSeries(false)
}

// IntersectionObserver 实例
let observer: IntersectionObserver | null = null

// 加载更多处理
const loadMoreTVSeries = () => {
  if (loading.value || loadingMore.value || noMore.value) return

  pagination.page++
  loadTVSeries(true)
}

// 设置 IntersectionObserver
const setupIntersectionObserver = () => {
  if (!scrollTrigger.value) return

  observer = new IntersectionObserver(
    (entries) => {
      const target = entries[0]
      if (target.isIntersecting) {
        loadMoreTVSeries()
      }
    },
    {
      root: null, // 使用视口作为根
      rootMargin: '300px', // 提前 300px 触发
      threshold: 0.1
    }
  )

  observer.observe(scrollTrigger.value)
}

// 清理 IntersectionObserver
const cleanupIntersectionObserver = () => {
  if (observer && scrollTrigger.value) {
    observer.unobserve(scrollTrigger.value)
    observer.disconnect()
    observer = null
  }
}

// 查看剧集详情
const handleViewTV = (tvId: number) => {
  router.push({
    path: `/tv/${tvId}`,
    query: { tab: 'tv' }
  })
}

// 获取状态样式类
const getStatusClass = (status: string) => {
  if (status === 'Returning Series' || status === 'In Production') {
    return 'status-ongoing'
  } else if (status === 'Ended') {
    return 'status-ended'
  } else if (status === 'Canceled') {
    return 'status-canceled'
  }
  return ''
}

// 获取状态显示文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'Returning Series': '连载中',
    'Ended': '已完结',
    'Canceled': '已取消',
    'In Production': '制作中'
  }
  return statusMap[status] || status
}

// 为每个图片生成随机动画延迟，避免同时加载时的"晃眼"效果
const getRandomAnimationDelay = () => {
  const delay = Math.random() * 1.5 // 0-1.5秒的随机延迟
  return {
    animationDelay: `${delay}s`
  }
}

// store 初始化完成后（initSettings 异步加载），若值发生变化则重新加载列表
watch(() => settingsStore.tvShowAnime, () => {
  pagination.page = 1
  noMore.value = false
  loadTVSeries()
})

onMounted(async () => {
  await Promise.all([
    loadTVSeries(),
    loadTrendingCollections()
  ])
  // 等待 DOM 更新后再设置 observer
  setTimeout(() => {
    setupIntersectionObserver()
  }, 100)
  window.addEventListener('resize', handleMobileResize)
})

onUnmounted(() => {
  cleanupIntersectionObserver()
  window.removeEventListener('resize', handleMobileResize)
})

// keep-alive 激活时恢复滚动位置
onActivated(() => {
  if (savedScrollPosition.value > 0) {
    nextTick(() => {
      // 查找实际的滚动容器
      const elMain = document.querySelector('.el-main') as HTMLElement

      if (elMain) {
        elMain.scrollTop = savedScrollPosition.value
      } else {
        window.scrollTo({
          top: savedScrollPosition.value,
          behavior: 'instant'
        })
      }
    })
  }
})

// keep-alive 停用时保存滚动位置
onDeactivated(() => {
  // 检测多个可能的滚动容器
  const windowScrollY = window.scrollY || document.documentElement.scrollTop
  const elMain = document.querySelector('.el-main') as HTMLElement
  const elMainScrollTop = elMain ? elMain.scrollTop : 0
  const bodyScrollTop = document.body ? document.body.scrollTop : 0

  // 优先使用非零的滚动值
  savedScrollPosition.value = elMainScrollTop || windowScrollY || bodyScrollTop
})
</script>

<style scoped>
.page-container {
  width: 100%;
  padding: 0;
  margin-top: -25px; /* 减少与顶部标签栏的间距 */
}

/* 工具栏样式移入 filter-header */
.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--nf-border-base);
}

.total-count {
  font-size: 16px;
  font-weight: 600;
  color: var(--nf-text-primary);
}

.search-input {
  width: 240px;
}



/* 筛选面板新样式 */
.filter-panel {
  background-color: var(--nf-bg-elevated);
  border-radius: var(--nf-radius-base);
  padding: 16px 20px;
  margin-bottom: 20px;
  border: 1px solid var(--nf-border-base);
  box-shadow: var(--nf-shadow-sm);
}

.filter-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed var(--nf-border-base);
}

.filter-row:last-child {
  border-bottom: none;
}

.filter-label {
  width: 60px;
  font-size: 14px;
  font-weight: 500;
  color: var(--nf-text-secondary);
  flex-shrink: 0;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.filter-tag {
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 16px;
  cursor: pointer;
  color: var(--nf-text-secondary);
  background-color: transparent;
  border: 1px solid var(--nf-border-base);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-tag:hover {
  color: var(--nf-primary);
  border-color: var(--nf-primary);
  background-color: rgba(64, 158, 255, 0.08);
}

.filter-tag.active {
  color: #fff;
  background-color: var(--nf-primary);
  border-color: var(--nf-primary);
  font-weight: 500;
}

.sort-icon {
  font-size: 12px;
}

.tv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.tv-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.tv-card:hover {
  transform: translateY(-4px);
}

.tv-poster {
  position: relative;
  width: 100%;
  height: 280px;
  background-color: var(--nf-bg-container);
  overflow: hidden;
}

.poster-image {
  width: 100%;
  height: 100%;
}

.image-slot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 48px;
  color: var(--nf-text-placeholder);
}

/* 图片加载动画 - 增强版shimmer效果 */
.image-loading {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--nf-bg-container) 0%,
    var(--nf-bg-elevated) 25%,
    var(--nf-bg-overlay) 50%,
    var(--nf-bg-elevated) 75%,
    var(--nf-bg-container) 100%
  );
  background-size: 300% 100%;
  animation: loading-shimmer 2s infinite ease-in-out;
  position: relative;
  overflow: hidden;
}

/* 添加光泽效果层 */
.image-loading::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.08) 50%,
    transparent 100%
  );
  animation: loading-gleam 2s infinite ease-in-out;
}

.loading-shimmer {
  width: 100%;
  height: 100%;
}

@keyframes loading-shimmer {
  0% {
    background-position: 300% 0;
  }
  100% {
    background-position: -300% 0;
  }
}

@keyframes loading-gleam {
  0% {
    left: -100%;
  }
  100% {
    left: 200%;
  }
}

.rating-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 4px 8px;
  background-color: rgba(110, 45, 200, 0.7);
  color: #fff;
  border-radius: 4px;
  font-size: 14px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 4px;
}

.local-badge {
  position: absolute;
  bottom: 10px;
  right: 10px;
  padding: 3px 7px;
  background-color: rgba(103, 194, 58, 0.85);
  color: white;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
}

.status-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 8px;
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-ongoing {
  background-color: var(--nf-success); /* 绿色 - 连载中/制作中 */
}

.status-ended {
  background-color: var(--nf-info); /* 灰色 - 已完结 */
}

.status-canceled {
  background-color: var(--nf-danger); /* 红色 - 已取消 */
}

.tv-info {
  padding: 12px;
}

.tv-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--nf-text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tv-meta {
  font-size: 12px;
  color: var(--nf-text-regular);
  margin-bottom: 8px;
}

.tv-genres {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 加载更多和结束提示 */
.loading-more,
.no-more {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 32px 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.loading-more .el-icon {
  font-size: 18px;
}

/* 无限滚动触发器（隐藏但占据空间） */
.scroll-trigger {
  height: 1px;
  width: 100%;
  visibility: hidden;
}

/* 移动端筛选切换按钮：PC端隐藏 */
.mobile-filter-toggle {
  display: none;
}

/* 深色主题覆盖：搜索输入框和日期选择器 */
.filter-panel :deep(.el-input .el-input__wrapper),
.filter-panel :deep(.el-date-editor.el-input__wrapper) {
  background-color: var(--nf-bg-container);
  box-shadow: 0 0 0 1px var(--nf-border-base) inset;
}

.filter-panel :deep(.el-input .el-input__wrapper:hover),
.filter-panel :deep(.el-date-editor.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--nf-border-light) inset;
}

.filter-panel :deep(.el-input .el-input__wrapper.is-focus),
.filter-panel :deep(.el-date-editor.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--nf-primary) inset;
}

.filter-panel :deep(.el-input__inner),
.filter-panel :deep(.el-input__inner::placeholder) {
  color: var(--nf-text-regular);
}

.filter-panel :deep(.el-input__inner::placeholder) {
  color: var(--nf-text-placeholder);
}

@media (max-width: 768px) {
  .search-input {
    width: 100%;
  }

  .filter-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .header-right {
    width: 100%;
  }
}
</style>
