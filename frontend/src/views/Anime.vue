<template>
  <div class="page-container">
    <!-- 回到顶部 -->
    <el-backtop target=".el-main" :right="40" :bottom="40" />

    <!-- 筛选面板 -->
    <div class="filter-panel">
      <!-- 顶部工具栏行 -->
      <div class="filter-header">
        <div class="header-left">
          <span class="total-count">共 {{ totalCount }} 部动画</span>
          <button class="mobile-filter-toggle" @click="filterExpanded = !filterExpanded">
            <el-icon><Filter /></el-icon>
            筛选
            <span v-if="activeFilterCount > 0" class="mobile-filter-badge">{{ activeFilterCount }}</span>
            <el-icon class="filter-toggle-arrow" :class="{ 'is-expanded': filterExpanded }"><ArrowDown /></el-icon>
          </button>
        </div>
        <div class="header-right">
          <el-input v-model="searchKeyword" placeholder="搜索动画..." :prefix-icon="Search" clearable class="search-input"
            @keyup.enter="handleSearch" @clear="handleSearch" />
        </div>
      </div>
      <div class="filter-rows-wrapper" :class="{ 'is-expanded': filterExpanded }">
      <!-- 分类行（电影/剧集） -->
      <div class="filter-row">
        <div class="filter-label">分类</div>
        <div class="filter-options">
          <div class="filter-tag" :class="{ active: !filters.mediaType }" @click="handleMediaTypeChange(undefined)">
            全部
          </div>
          <div class="filter-tag" :class="{ active: filters.mediaType === 'movie' }"
            @click="handleMediaTypeChange('movie')">
            电影
          </div>
          <div class="filter-tag" :class="{ active: filters.mediaType === 'tv' }" @click="handleMediaTypeChange('tv')">
            剧集
          </div>
        </div>
      </div>

      <!-- 排序行 -->
      <div class="filter-row">
        <div class="filter-label">排序</div>
        <div class="filter-options">
          <div v-for="option in sortOptions" :key="option.value" class="filter-tag"
            :class="{ active: filters.sortBy === option.value }" @click="handleSortChange(option.value)">
            {{ option.label }}
            <el-icon v-if="filters.sortBy === option.value" class="sort-icon">
              <Sort v-if="filters.order === 'desc'" />
              <SortUp v-else />
            </el-icon>
          </div>
        </div>
      </div>

      <!-- 年份行 -->
      <div class="filter-row">
        <div class="filter-label">年份</div>
        <div class="filter-options">
          <div class="filter-tag" :class="{ active: !filters.year }" @click="handleYearChange(null)">
            全部
          </div>
          <div v-for="year in yearOptions" :key="year" class="filter-tag"
            :class="{ active: filters.year && filters.year.getFullYear() === year }"
            @click="handleYearQuickChange(year)">
            {{ year }}
          </div>
          <el-date-picker v-model="filters.year" type="year" placeholder="更多"
            :disabled-date="(date: Date) => date.getFullYear() > new Date().getFullYear()"
            style="width: 100px; margin-left: 8px;" size="small" @change="handleFilterChange" />
        </div>
      </div>

      <!-- 地区行 -->
      <div class="filter-row">
        <div class="filter-label">地区</div>
        <div class="filter-options">
          <div class="filter-tag" :class="{ active: !filters.country }" @click="handleCountryChange('')">
            全部
          </div>
          <div v-for="country in countryOptions" :key="country" class="filter-tag"
            :class="{ active: filters.country === country }" @click="handleCountryChange(country)">
            {{ country }}
          </div>
        </div>
      </div>

      <!-- 评分行 -->
      <div class="filter-row">
        <div class="filter-label">评分</div>
        <div class="filter-options">
          <div class="filter-tag" :class="{ active: !filters.minRating }" @click="handleRatingChange(undefined)">
            全部
          </div>
          <div v-for="rating in ratingOptions" :key="rating.value" class="filter-tag"
            :class="{ active: filters.minRating === rating.value }" @click="handleRatingChange(rating.value)">
            {{ rating.label }}
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 动画卡片列表 -->
    <div v-loading="loading && animeList.length === 0" class="anime-grid">
      <el-card v-for="item in animeList" :key="item._key" class="anime-card" :body-style="{ padding: '0px' }"
        shadow="hover" @click="handleViewDetail(item)">
        <div class="anime-poster">
          <el-image v-if="item.posterUrl" :src="getProxiedImageUrl(item.posterUrl)" fit="cover" lazy
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
          <div v-if="item.ratingDouban || item.ratingTmdb || item.ratingImdb" class="rating-badge">
            <el-icon>
              <Star />
            </el-icon>
            {{ item.ratingDouban || item.ratingTmdb || item.ratingImdb }}
          </div>

          <!-- 类型标签（电影/剧集） -->
          <div class="media-type-badge" :class="item._mediaType === 'movie' ? 'type-movie' : 'type-tv'">
            {{ item._mediaType === 'movie' ? '电影' : '剧集' }}
          </div>
        </div>

        <div class="anime-info">
          <div class="anime-title" :title="item.title">{{ item.title }}</div>
          <div class="anime-meta">
            <span v-if="item.year">{{ item.year }}</span>
            <span v-if="item._mediaType === 'movie' && item.runtime"> • {{ item.runtime }}分钟</span>
            <span v-if="item._mediaType === 'tv' && item.numberOfSeasons"> • {{ item.numberOfSeasons }}季</span>
          </div>
          <div v-if="item.genres && item.genres.length" class="anime-genres">
            <el-tag v-for="genre in item.genres.filter((g: string) => g !== '动画').slice(0, 3)" :key="genre" size="small"
              effect="plain">
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
    <div v-if="noMore && animeList.length > 0" class="no-more">
      已加载全部内容
    </div>

    <!-- 无限滚动触发器 -->
    <div ref="scrollTrigger" class="scroll-trigger"></div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && animeList.length === 0" description="暂无动画数据">
      <el-button type="primary" @click="$router.push('/resources')"> 去识别PT资源 </el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, onActivated, onDeactivated, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Picture, Star, Loading, Sort, SortUp, Filter, ArrowDown } from '@element-plus/icons-vue'
import api from '@/api'
import type { UnifiedMovie, UnifiedTV } from '@/types'
import { getProxiedImageUrl } from '@/utils'

// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'AnimeView'
})

const router = useRouter()

// 合并后的动画项类型
interface AnimeItem {
  _key: string          // 唯一 key: "movie_123" 或 "tv_456"
  _mediaType: 'movie' | 'tv'
  _sortDate: string     // 用于排序的日期
  id: number
  title: string
  originalTitle?: string
  year?: number
  ratingTmdb?: number
  ratingDouban?: number
  ratingImdb?: number
  genres?: string[]
  posterUrl?: string
  ptResourceCount: number
  hasFreeResource: boolean
  createdAt: string
  updatedAt: string
  // 电影特有
  runtime?: number
  // 剧集特有
  numberOfSeasons?: number
  status?: string
}

// 状态
const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const searchKeyword = ref('')
const animeList = ref<AnimeItem[]>([])
const scrollTrigger = ref<HTMLElement | null>(null)

// 分别记录两个数据源的分页状态
const moviePagination = reactive({ page: 1, total: 0, noMore: false })
const tvPagination = reactive({ page: 1, total: 0, noMore: false })
const pageSize = 20

// 滚动位置保存
const savedScrollPosition = ref(0)

// 总数
const totalCount = computed(() => moviePagination.total + tvPagination.total)

// 筛选条件
const filters = reactive({
  mediaType: undefined as 'movie' | 'tv' | undefined,
  year: undefined as Date | undefined,
  country: undefined as string | undefined,
  sortBy: 'created_at',
  order: 'desc',
  minRating: undefined as number | undefined,
})

// 选项配置
const sortOptions = [
  { label: '最新添加', value: 'created_at' },
  { label: '最高评分', value: 'rating' },
  { label: '发行年份', value: 'year' },
  { label: '名称', value: 'title' }
]

const countryOptions = [
  '日本', '中国大陆', '美国', '韩国', '香港', '台湾', '英国', '法国', '其他'
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
  if (filters.mediaType) count++
  if (filters.year) count++
  if (filters.country) count++
  if (filters.minRating) count++
  if (searchKeyword.value) count++
  return count
})
const handleMobileResize = () => {
  if (window.innerWidth > 768) filterExpanded.value = true
}

// 将电影转为统一的 AnimeItem
function movieToAnimeItem(movie: UnifiedMovie): AnimeItem {
  return {
    _key: `movie_${movie.id}`,
    _mediaType: 'movie',
    _sortDate: movie.createdAt,
    id: movie.id,
    title: movie.title,
    originalTitle: movie.originalTitle,
    year: movie.year,
    ratingTmdb: movie.ratingTmdb,
    ratingDouban: movie.ratingDouban,
    ratingImdb: movie.ratingImdb,
    genres: movie.genres,
    posterUrl: movie.posterUrl,
    ptResourceCount: movie.ptResourceCount,
    hasFreeResource: movie.hasFreeResource,
    createdAt: movie.createdAt,
    updatedAt: movie.updatedAt,
    runtime: movie.runtime,
  }
}

// 将剧集转为统一的 AnimeItem
function tvToAnimeItem(tv: UnifiedTV): AnimeItem {
  return {
    _key: `tv_${tv.id}`,
    _mediaType: 'tv',
    _sortDate: tv.createdAt,
    id: tv.id,
    title: tv.title,
    originalTitle: tv.originalTitle,
    year: tv.year,
    ratingTmdb: tv.ratingTmdb,
    ratingDouban: tv.ratingDouban,
    ratingImdb: tv.ratingImdb,
    genres: tv.genres,
    posterUrl: tv.posterUrl,
    ptResourceCount: tv.ptResourceCount,
    hasFreeResource: tv.hasFreeResource,
    createdAt: tv.createdAt,
    updatedAt: tv.updatedAt,
    numberOfSeasons: tv.numberOfSeasons,
    status: tv.status,
  }
}

// 排序合并
function sortItems(items: AnimeItem[]): AnimeItem[] {
  return items.sort((a, b) => {
    let valA: any, valB: any
    if (filters.sortBy === 'rating') {
      valA = a.ratingDouban || a.ratingTmdb || a.ratingImdb || 0
      valB = b.ratingDouban || b.ratingTmdb || b.ratingImdb || 0
    } else if (filters.sortBy === 'year') {
      valA = a.year || 0
      valB = b.year || 0
    } else if (filters.sortBy === 'title') {
      valA = a.title
      valB = b.title
      return filters.order === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA)
    } else {
      // created_at
      valA = a.createdAt || ''
      valB = b.createdAt || ''
      return filters.order === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA)
    }
    return filters.order === 'asc' ? valA - valB : valB - valA
  })
}

// 构建公共请求参数
function buildCommonParams() {
  return {
    pageSize,
    search: searchKeyword.value || undefined,
    year: filters.year ? filters.year.getFullYear() : undefined,
    genre: '动画',
    country: filters.country || undefined,
    sortBy: filters.sortBy,
    order: filters.order,
    minRating: filters.minRating,
  }
}

// 加载动画列表
const loadAnime = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const commonParams = buildCommonParams()
    const needMovie = !filters.mediaType || filters.mediaType === 'movie'
    const needTV = !filters.mediaType || filters.mediaType === 'tv'

    const promises: Promise<any>[] = []

    if (needMovie && !moviePagination.noMore) {
      promises.push(
        api.movie.getMovieList({
          ...commonParams,
          page: moviePagination.page,
        })
      )
    } else {
      promises.push(Promise.resolve(null))
    }

    if (needTV && !tvPagination.noMore) {
      promises.push(
        api.tv.getTVList({
          ...commonParams,
          page: tvPagination.page,
        })
      )
    } else {
      promises.push(Promise.resolve(null))
    }

    const [movieRes, tvRes] = await Promise.all(promises)

    let newMovieItems: AnimeItem[] = []
    let newTVItems: AnimeItem[] = []

    if (movieRes?.data) {
      const movieItems = (movieRes.data.items || []).map(movieToAnimeItem)
      newMovieItems = movieItems
      moviePagination.total = movieRes.data.total || 0
      if (!append) {
        moviePagination.noMore = movieItems.length >= moviePagination.total
      } else {
        // 追加模式下检查是否当页返回数据为空或不足一页
        moviePagination.noMore = movieItems.length < pageSize
      }
    } else if (!needMovie) {
      moviePagination.total = 0
    }

    if (tvRes?.data) {
      const tvItems = (tvRes.data.items || []).map(tvToAnimeItem)
      newTVItems = tvItems
      tvPagination.total = tvRes.data.total || 0
      if (!append) {
        tvPagination.noMore = tvItems.length >= tvPagination.total
      } else {
        tvPagination.noMore = tvItems.length < pageSize
      }
    } else if (!needTV) {
      tvPagination.total = 0
    }

    const newItems = sortItems([...newMovieItems, ...newTVItems])

    if (append) {
      animeList.value = [...animeList.value, ...newItems]
    } else {
      animeList.value = newItems
    }

    // 检查是否全部加载完
    const movieDone = !needMovie || moviePagination.noMore
    const tvDone = !needTV || tvPagination.noMore
    noMore.value = movieDone && tvDone
  } catch (error) {
    console.error('Failed to load anime:', error)
    ElMessage.error('加载动画列表失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  resetPagination()
  loadAnime(false)
}

// 处理筛选变化
const handleFilterChange = () => {
  resetPagination()
  loadAnime(false)
}

// 重置分页
const resetPagination = () => {
  moviePagination.page = 1
  moviePagination.noMore = false
  tvPagination.page = 1
  tvPagination.noMore = false
  noMore.value = false
}

// 处理排序变化
const handleSortChange = (value: string) => {
  if (filters.sortBy === value) {
    filters.order = filters.order === 'desc' ? 'asc' : 'desc'
  } else {
    filters.sortBy = value
    filters.order = 'desc'
  }
  handleFilterChange()
}

// 处理分类变化
const handleMediaTypeChange = (type: 'movie' | 'tv' | undefined) => {
  filters.mediaType = type
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
    filters.year = undefined
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

// IntersectionObserver
let observer: IntersectionObserver | null = null

const loadMore = () => {
  if (loading.value || loadingMore.value || noMore.value) return

  const needMovie = !filters.mediaType || filters.mediaType === 'movie'
  const needTV = !filters.mediaType || filters.mediaType === 'tv'

  if (needMovie && !moviePagination.noMore) {
    moviePagination.page++
  }
  if (needTV && !tvPagination.noMore) {
    tvPagination.page++
  }

  loadAnime(true)
}

const setupIntersectionObserver = () => {
  if (!scrollTrigger.value) return

  observer = new IntersectionObserver(
    (entries) => {
      const target = entries[0]
      if (target.isIntersecting) {
        loadMore()
      }
    },
    {
      root: null,
      rootMargin: '300px',
      threshold: 0.1
    }
  )

  observer.observe(scrollTrigger.value)
}

const cleanupIntersectionObserver = () => {
  if (observer && scrollTrigger.value) {
    observer.unobserve(scrollTrigger.value)
    observer.disconnect()
    observer = null
  }
}

// 查看详情
const handleViewDetail = (item: AnimeItem) => {
  if (item._mediaType === 'movie') {
    router.push({
      path: `/movies/${item.id}`,
      query: { tab: 'anime' }
    })
  } else {
    router.push({
      path: `/tv/${item.id}`,
      query: { tab: 'anime' }
    })
  }
}

// 随机动画延迟
const getRandomAnimationDelay = () => {
  const delay = Math.random() * 1.5
  return { animationDelay: `${delay}s` }
}

onMounted(async () => {
  await loadAnime()
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
      const elMain = document.querySelector('.el-main') as HTMLElement
      if (elMain) {
        elMain.scrollTop = savedScrollPosition.value
      } else {
        window.scrollTo({ top: savedScrollPosition.value, behavior: 'instant' })
      }
    })
  }
})

// keep-alive 停用时保存滚动位置
onDeactivated(() => {
  const windowScrollY = window.scrollY || document.documentElement.scrollTop
  const elMain = document.querySelector('.el-main') as HTMLElement
  const elMainScrollTop = elMain ? elMain.scrollTop : 0
  const bodyScrollTop = document.body ? document.body.scrollTop : 0
  savedScrollPosition.value = elMainScrollTop || windowScrollY || bodyScrollTop
})
</script>

<style scoped>
.page-container {
  width: 100%;
  padding: 0;
  margin-top: -25px;
}

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

.anime-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.anime-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.anime-card:hover {
  transform: translateY(-4px);
}

.anime-poster {
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

.image-loading {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, var(--nf-bg-container) 25%, var(--nf-bg-overlay) 50%, var(--nf-bg-container) 75%);
  background-size: 200% 100%;
  animation: loading-shimmer 2.5s infinite ease-in-out;
}

.loading-shimmer {
  width: 100%;
  height: 100%;
}

@keyframes loading-shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
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

.media-type-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 8px;
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.type-movie {
  background-color: var(--nf-primary);
}

.type-tv {
  background-color: var(--nf-success);
}

.anime-info {
  padding: 12px;
}

.anime-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--nf-text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.anime-meta {
  font-size: 12px;
  color: var(--nf-text-regular);
  margin-bottom: 8px;
}

.anime-genres {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

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

.scroll-trigger {
  height: 1px;
  width: 100%;
  visibility: hidden;
}

/* 移动端筛选切换按钮：PC端隐藏 */
.mobile-filter-toggle {
  display: none;
}

/* 深色主题覆盖 */
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
