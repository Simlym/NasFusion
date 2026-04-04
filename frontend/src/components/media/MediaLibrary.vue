<template>
  <div class="media-library-page">
    <!-- 顶部筛选栏 -->
    <div class="filter-bar">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="媒体服务器">
          <el-select
            v-model="filters.config_id"
            placeholder="选择服务器"
            clearable
            @change="handleServerChange"
            style="width: 200px"
          >
            <el-option
              v-for="config in configs"
              :key="config.id"
              :label="config.name"
              :value="config.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="媒体库">
          <el-select
            v-model="filters.library_id"
            placeholder="全部目录"
            clearable
            @change="handleFilterChange"
            style="width: 200px"
            :disabled="!filters.config_id"
          >
            <el-option
              v-for="lib in libraries"
              :key="lib.id"
              :label="getLibraryLabel(lib)"
              :value="lib.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="媒体类型">
          <el-select
            v-model="filters.media_type"
            placeholder="全部"
            clearable
            @change="handleFilterChange"
            style="width: 140px"
          >
            <el-option label="电影" value="movie" />
            <el-option label="电视剧" value="tv" />
            <el-option label="音乐" value="music" />
            <el-option label="动漫" value="anime" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词" v-if="viewLevel === 'root'">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索标题"
            clearable
            @input="handleSearchDebounced"
            style="width: 200px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :icon="Refresh" @click="loadItems" :loading="loading">
            刷新
          </el-button>
          <el-button type="success" :icon="Connection" @click="handleSync" :loading="syncing">
            同步媒体库
          </el-button>
        </el-form-item>

        <!-- 视图切换（仅根级别显示） -->
        <el-form-item v-if="viewLevel === 'root'" style="margin-left: auto; margin-right: 0">
          <el-button-group>
            <el-tooltip content="竖版海报" placement="top">
              <el-button
                :type="viewMode === 'portrait' ? 'primary' : 'default'"
                :icon="Grid"
                @click="viewMode = 'portrait'"
              />
            </el-tooltip>
            <el-tooltip content="横版海报" placement="top">
              <el-button
                :type="viewMode === 'landscape' ? 'primary' : 'default'"
                :icon="List"
                @click="viewMode = 'landscape'"
              />
            </el-tooltip>
          </el-button-group>
        </el-form-item>
      </el-form>
    </div>

    <!-- 面包屑导航 -->
    <div v-if="viewLevel !== 'root'" class="breadcrumb-bar">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item>
          <a @click.prevent="navigateToRoot" class="breadcrumb-link">媒体库</a>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-if="currentSeries">
          <a
            v-if="viewLevel === 'episodes'"
            @click.prevent="navigateToSeries"
            class="breadcrumb-link"
          >{{ currentSeries.name }}</a>
          <span v-else>{{ currentSeries.name }}</span>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-if="viewLevel === 'episodes' && currentSeasonLabel">
          <span>{{ currentSeasonLabel }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 统计信息（仅根级别） -->
    <div v-if="viewLevel === 'root' && statistics" class="stats-bar">
      <el-tag type="info">总计: {{ statistics.total_count || 0 }}</el-tag>
      <el-tag v-if="statistics.by_type?.movie" type="primary">电影: {{ statistics.by_type.movie }}</el-tag>
      <el-tag v-if="statistics.by_type?.tv" type="success">电视剧: {{ statistics.by_type.tv }}</el-tag>
      <el-tag type="warning">已匹配文件: {{ statistics.matched_file_count || 0 }}</el-tag>
      <el-tag type="danger">已匹配资源: {{ statistics.matched_unified_count || 0 }}</el-tag>
    </div>

    <!-- ==================== 根级别：Movie + Series 海报网格 ==================== -->
    <div v-if="viewLevel === 'root'" v-loading="loading" class="cards-container">
      <el-empty v-if="!loading && items.length === 0" description="暂无媒体项" />

      <!-- 竖版海报 -->
      <el-row v-else-if="viewMode === 'portrait'" :gutter="16">
        <el-col
          v-for="item in items"
          :key="item.id"
          :xs="12" :sm="8" :md="6" :lg="4" :xl="3"
        >
          <div class="media-card" @click="handleItemClick(item)">
            <div class="card-poster">
              <el-image
                v-if="item.image_url"
                :src="item.image_url"
                fit="cover"
                lazy
                class="poster-image"
              >
                <template #placeholder>
                  <div class="poster-placeholder shimmer"></div>
                </template>
                <template #error>
                  <div class="poster-placeholder">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div v-else class="poster-placeholder">
                <el-icon><Picture /></el-icon>
              </div>

              <div class="card-overlay">
                <div class="overlay-top">
                  <el-tag size="small" :type="getItemTypeTag(item.item_type)" class="type-tag">
                    {{ getItemTypeLabel(item.item_type) }}
                  </el-tag>
                </div>
                <div class="overlay-bottom">
                  <div class="overlay-meta">
                    <span v-if="item.year" class="meta-year">{{ item.year }}</span>
                    <span v-if="item.play_count > 0" class="meta-plays">
                      <el-icon><VideoPlay /></el-icon>
                      {{ item.play_count }}
                    </span>
                  </div>
                  <div class="overlay-actions">
                    <el-button
                      v-if="item.web_url"
                      type="primary"
                      circle
                      size="small"
                      :icon="VideoPlay"
                      @click.stop="openInMediaServer(item)"
                    />
                  </div>
                </div>
              </div>

              <!-- Series 季集统计角标 -->
              <div v-if="item.item_type === 'Series' && item.season_count" class="series-badge">
                {{ item.season_count }}季 · {{ item.episode_count }}集
              </div>

            </div>

            <div class="card-info">
              <div class="card-title" :title="item.name">{{ item.name }}</div>
              <div v-if="item.original_name && item.original_name !== item.name" class="card-subtitle" :title="item.original_name">
                {{ item.original_name }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 横版海报 -->
      <el-row v-else :gutter="16">
        <el-col
          v-for="item in items"
          :key="item.id"
          :xs="12" :sm="8" :md="6" :lg="4" :xl="3"
        >
          <div class="media-card-landscape" @click="handleItemClick(item)">
            <div class="landscape-poster">
              <el-image
                v-if="item.image_url"
                :src="item.image_url"
                fit="cover"
                lazy
                class="landscape-poster-image"
              >
                <template #placeholder>
                  <div class="landscape-poster-placeholder shimmer"></div>
                </template>
                <template #error>
                  <div class="landscape-poster-placeholder">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div v-else class="landscape-poster-placeholder">
                <el-icon><Picture /></el-icon>
              </div>

              <div class="landscape-overlay">
                <div class="overlay-top">
                  <el-tag size="small" :type="getItemTypeTag(item.item_type)" class="type-tag">
                    {{ getItemTypeLabel(item.item_type) }}
                  </el-tag>
                </div>
                <div class="overlay-bottom">
                  <div class="overlay-meta">
                    <span v-if="item.year" class="meta-year">{{ item.year }}</span>
                    <span v-if="item.play_count > 0" class="meta-plays">
                      <el-icon><VideoPlay /></el-icon>
                      {{ item.play_count }}
                    </span>
                  </div>
                  <div class="overlay-actions">
                    <el-button
                      v-if="item.web_url"
                      type="primary"
                      circle
                      size="small"
                      :icon="VideoPlay"
                      @click.stop="openInMediaServer(item)"
                    />
                  </div>
                </div>
              </div>

              <!-- Series 季集统计角标 -->
              <div v-if="item.item_type === 'Series' && item.season_count" class="series-badge">
                {{ item.season_count }}季 · {{ item.episode_count }}集
              </div>

            </div>

            <div class="card-info">
              <div class="card-title" :title="item.name">{{ item.name }}</div>
              <div v-if="item.original_name && item.original_name !== item.name" class="card-subtitle" :title="item.original_name">
                {{ item.original_name }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- ==================== 季级别：Series > Seasons 网格 ==================== -->
    <div v-else-if="viewLevel === 'seasons'" v-loading="loadingSeasons" class="cards-container">
      <!-- 剧集信息头 -->
      <div v-if="currentSeries" class="series-header">
        <div class="series-header-poster">
          <el-image
            v-if="currentSeries.image_url"
            :src="currentSeries.image_url"
            fit="cover"
            class="series-header-image"
          >
            <template #error>
              <div class="poster-placeholder"><el-icon><Picture /></el-icon></div>
            </template>
          </el-image>
        </div>
        <div class="series-header-info">
          <h2 class="series-title">{{ currentSeries.name }}</h2>
          <div v-if="currentSeries.original_name && currentSeries.original_name !== currentSeries.name" class="series-original-name">
            {{ currentSeries.original_name }}
          </div>
          <div class="series-meta">
            <el-tag v-if="currentSeries.year" size="small">{{ currentSeries.year }}</el-tag>
            <el-tag v-if="currentSeries.community_rating" type="warning" size="small">
              {{ currentSeries.community_rating }}
            </el-tag>
            <span v-if="currentSeries.genres?.length" class="series-genres">
              {{ currentSeries.genres.join(' / ') }}
            </span>
          </div>
          <p v-if="currentSeries.overview" class="series-overview">{{ currentSeries.overview }}</p>
        </div>
      </div>

      <el-empty v-if="!loadingSeasons && seasons.length === 0" description="暂无季信息" />

      <el-row v-else :gutter="16">
        <el-col
          v-for="season in seasons"
          :key="season.season_number"
          :xs="12" :sm="8" :md="6" :lg="4" :xl="3"
        >
          <div class="media-card" @click="navigateToEpisodes(season)">
            <div class="card-poster">
              <el-image
                v-if="season.image_url"
                :src="season.image_url"
                fit="cover"
                lazy
                class="poster-image"
              >
                <template #placeholder>
                  <div class="poster-placeholder shimmer"></div>
                </template>
                <template #error>
                  <div class="poster-placeholder">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div v-else class="poster-placeholder">
                <el-icon><Picture /></el-icon>
              </div>

              <div class="card-overlay card-overlay--visible">
                <div class="overlay-bottom">
                  <div class="overlay-meta">
                    <span class="meta-year">{{ season.episode_count }} 集</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="card-info">
              <div class="card-title">{{ season.season_name }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- ==================== 集级别：Series > Season > Episodes 列表 ==================== -->
    <div v-else-if="viewLevel === 'episodes'" v-loading="loadingEpisodes" class="cards-container">
      <el-empty v-if="!loadingEpisodes && episodes.length === 0" description="暂无剧集" />

      <div v-else class="episodes-list">
        <div
          v-for="ep in episodes"
          :key="ep.id"
          class="episode-item"
          @click="openInMediaServer(ep)"
        >
          <div class="episode-thumb">
            <el-image
              v-if="ep.image_url"
              :src="ep.image_url"
              fit="cover"
              lazy
              class="episode-thumb-image"
            >
              <template #error>
                <div class="episode-thumb-placeholder">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="episode-thumb-placeholder">
              <el-icon><Picture /></el-icon>
            </div>
            <div v-if="ep.runtime_seconds" class="episode-duration">
              {{ formatDuration(ep.runtime_seconds) }}
            </div>
          </div>

          <div class="episode-info">
            <div class="episode-number">
              E{{ String(ep.episode_number || 0).padStart(2, '0') }}
            </div>
            <div class="episode-title">{{ ep.name }}</div>
            <div v-if="ep.overview" class="episode-overview">{{ ep.overview }}</div>
            <div class="episode-meta">
              <span v-if="ep.premiere_date" class="episode-date">
                {{ formatDate(ep.premiere_date) }}
              </span>
              <el-tag v-if="ep.play_count > 0" type="success" size="small">
                已观看 {{ ep.play_count > 1 ? ep.play_count + '次' : '' }}
              </el-tag>
              <el-tag v-if="ep.resolution" size="small">{{ ep.resolution }}</el-tag>
            </div>
          </div>

          <div class="episode-actions">
            <el-button
              v-if="ep.web_url"
              type="primary"
              size="small"
              :icon="VideoPlay"
              circle
              @click.stop="openInMediaServer(ep)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 无限滚动触发点（仅根级别） -->
    <div v-if="viewLevel === 'root'" ref="scrollTrigger" class="scroll-trigger"></div>

    <!-- 加载更多 / 全部加载完（仅根级别） -->
    <div v-if="viewLevel === 'root' && loadingMore" class="load-status">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中…</span>
    </div>
    <div v-else-if="viewLevel === 'root' && noMore && items.length > 0" class="load-status load-status--done">
      已加载全部 {{ pagination.total }} 项
    </div>

    <!-- 同步对话框 -->
    <el-dialog
      v-model="syncDialog.visible"
      title="同步媒体库"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="同步模式">
          <el-radio-group v-model="syncDialog.mode" class="sync-mode-group">
            <el-radio value="incremental" class="sync-mode-radio">
              <div class="sync-mode-content">
                <span class="sync-mode-title">增量同步</span>
                <span class="sync-mode-desc">仅同步最近修改的媒体项，速度快，适合日常使用</span>
              </div>
            </el-radio>
            <el-radio value="full" class="sync-mode-radio">
              <div class="sync-mode-content">
                <span class="sync-mode-title">全量同步</span>
                <span class="sync-mode-desc">扫描所有媒体项，确保数据完整，适合首次同步或数据修复</span>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="syncDialog.mode === 'incremental'" label="时间范围">
          <el-select v-model="syncDialog.hours" style="width: 200px;">
            <el-option label="最近 1 小时" :value="1" />
            <el-option label="最近 6 小时" :value="6" />
            <el-option label="最近 12 小时" :value="12" />
            <el-option label="最近 24 小时（推荐）" :value="24" />
            <el-option label="最近 48 小时" :value="48" />
            <el-option label="最近 72 小时" :value="72" />
            <el-option label="最近 7 天" :value="168" />
          </el-select>
        </el-form-item>

        <el-alert
          v-if="syncDialog.mode === 'incremental'"
          title="提示"
          type="info"
          :closable="false"
          style="margin-top: 12px;"
        >
          增量同步会自动匹配本地文件，并清理已删除的媒体项
        </el-alert>

        <el-alert
          v-if="syncDialog.mode === 'full'"
          title="注意"
          type="warning"
          :closable="false"
          style="margin-top: 12px;"
        >
          全量同步可能需要较长时间（取决于媒体库大小），请耐心等待
        </el-alert>
      </el-form>

      <template #footer>
        <el-button @click="syncDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="syncing" @click="confirmSync">
          开始同步
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Search, Refresh, Connection, Picture, VideoPlay, Grid, List, Loading } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { debounce } from 'lodash-es'
import {
  getMediaServerConfigs,
  getMediaServerLibraryItems,
  syncMediaServerLibrary,
  getMediaServerLibraryStatistics,
  getMediaServerLibraries,
  getSeriesSeasons,
  getSeasonEpisodes
} from '@/api/modules/mediaServer'
import type { MediaServerConfig, MediaServerLibrary } from '@/types/mediaServer'

const route = useRoute()

// ==================== 视图层级状态 ====================
const viewLevel = ref<'root' | 'seasons' | 'episodes'>('root')
const currentSeries = ref<any>(null)
const currentSeasonNumber = ref<number>(0)
const currentSeasonLabel = ref<string>('')
const seasons = ref<any[]>([])
const episodes = ref<any[]>([])
const loadingSeasons = ref(false)
const loadingEpisodes = ref(false)

// ==================== 基础状态 ====================
const configs = ref<MediaServerConfig[]>([])
const libraries = ref<MediaServerLibrary[]>([])
const items = ref<any[]>([])
const statistics = ref<any>(null)
const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const syncing = ref(false)
const scrollTrigger = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const filters = ref({
  config_id: undefined as number | undefined,
  library_id: undefined as string | undefined,
  media_type: undefined as string | undefined,
  keyword: ''
})

const pagination = ref({
  page: 1,
  page_size: 48,
  total: 0
})

const sortField = ref('synced_at')
const sortOrder = ref(true)
const viewMode = ref<'portrait' | 'landscape'>('portrait')

// ==================== 导航方法 ====================
const navigateToRoot = () => {
  viewLevel.value = 'root'
  currentSeries.value = null
  seasons.value = []
  episodes.value = []
}

const navigateToSeries = () => {
  viewLevel.value = 'seasons'
  episodes.value = []
}

const handleItemClick = (item: any) => {
  if (item.item_type === 'Series') {
    loadSeriesSeasons(item)
  } else {
    openInMediaServer(item)
  }
}

const loadSeriesSeasons = async (seriesItem: any) => {
  if (!filters.value.config_id) return

  loadingSeasons.value = true
  viewLevel.value = 'seasons'

  try {
    const res = await getSeriesSeasons(filters.value.config_id, seriesItem.server_item_id)
    currentSeries.value = res.data.series || seriesItem
    seasons.value = res.data.seasons || []
  } catch (error: any) {
    console.error('加载季信息失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载季信息失败')
    navigateToRoot()
  } finally {
    loadingSeasons.value = false
  }
}

const navigateToEpisodes = async (season: any) => {
  if (!filters.value.config_id || !currentSeries.value) return

  loadingEpisodes.value = true
  viewLevel.value = 'episodes'
  currentSeasonNumber.value = season.season_number
  currentSeasonLabel.value = season.season_name

  try {
    const res = await getSeasonEpisodes(
      filters.value.config_id,
      currentSeries.value.server_item_id,
      season.season_number
    )
    episodes.value = res.data.episodes || []
  } catch (error: any) {
    console.error('加载剧集失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载剧集失败')
    navigateToSeries()
  } finally {
    loadingEpisodes.value = false
  }
}

// ==================== 数据加载 ====================
const loadConfigs = async () => {
  try {
    const res = await getMediaServerConfigs()
    configs.value = res.data
    const queryConfigId = route.query.config_id ? Number(route.query.config_id) : undefined
    if (queryConfigId && configs.value.some(c => c.id === queryConfigId)) {
      filters.value.config_id = queryConfigId
    } else if (configs.value.length > 0 && !filters.value.config_id) {
      filters.value.config_id = configs.value[0].id
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const loadLibraries = async () => {
  if (!filters.value.config_id) {
    libraries.value = []
    return
  }
  try {
    const res = await getMediaServerLibraries(filters.value.config_id)
    libraries.value = res.data
  } catch (error) {
    console.error('加载媒体库列表失败:', error)
    libraries.value = []
  }
}

const loadItems = async (isLoadMore = false) => {
  if (!filters.value.config_id) {
    items.value = []
    pagination.value.total = 0
    return
  }

  if (isLoadMore) {
    loadingMore.value = true
  } else {
    loading.value = true
    pagination.value.page = 1
    items.value = []
    noMore.value = false
  }

  try {
    const res = await getMediaServerLibraryItems(filters.value.config_id, {
      library_id: filters.value.library_id,
      media_type: filters.value.media_type,
      item_types: 'Movie,Series',
      keyword: filters.value.keyword || undefined,
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      order_by: sortField.value,
      order_desc: sortOrder.value
    })

    if (isLoadMore) {
      items.value.push(...res.data.items)
    } else {
      items.value = res.data.items
    }
    pagination.value.total = res.data.total

    if (items.value.length >= pagination.value.total) {
      noMore.value = true
    }
  } catch (error: any) {
    console.error('加载媒体项失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (loading.value || loadingMore.value || noMore.value) return
  pagination.value.page++
  loadItems(true)
}

const setupObserver = () => {
  if (!scrollTrigger.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting) loadMore()
    },
    { rootMargin: '300px', threshold: 0.1 }
  )
  observer.observe(scrollTrigger.value)
}

const cleanupObserver = () => {
  observer?.disconnect()
  observer = null
}

const loadStatistics = async () => {
  if (!filters.value.config_id) return
  try {
    const res = await getMediaServerLibraryStatistics(filters.value.config_id)
    statistics.value = res.data
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// ==================== 同步 ====================
const syncDialog = reactive({
  visible: false,
  mode: 'incremental' as 'full' | 'incremental',
  hours: 24
})

const handleSync = () => {
  if (!filters.value.config_id) {
    ElMessage.warning('请先选择媒体服务器')
    return
  }
  syncDialog.visible = true
}

const confirmSync = async () => {
  syncing.value = true
  syncDialog.visible = false

  try {
    const res = await syncMediaServerLibrary(filters.value.config_id, {
      match_files: true,
      sync_mode: syncDialog.mode,
      incremental_hours: syncDialog.mode === 'incremental' ? syncDialog.hours : undefined
    })

    ElMessage.success({
      message: res.data.message,
      duration: 5000
    })

    setTimeout(() => {
      noMore.value = false
      loadItems()
      loadStatistics()
    }, 3000)
  } catch (error: any) {
    console.error('同步失败:', error)
    ElMessage.error(error.response?.data?.detail || '同步失败')
  } finally {
    syncing.value = false
  }
}

// ==================== 筛选处理 ====================
const handleFilterChange = () => {
  navigateToRoot()
  loadItems()
  loadStatistics()
}

const handleServerChange = async () => {
  filters.value.library_id = undefined
  navigateToRoot()
  await loadLibraries()
  handleFilterChange()
}

const handleSearchDebounced = debounce(() => {
  loadItems()
}, 500)

// ==================== 工具方法 ====================
const openInMediaServer = (item: any) => {
  if (item.web_url) {
    window.open(item.web_url, '_blank')
  }
}

const getItemTypeTag = (type: string) => {
  const typeMap: Record<string, any> = {
    Movie: 'primary',
    Episode: 'success',
    Series: 'info',
    Season: 'warning'
  }
  return typeMap[type] || ''
}

const getItemTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    Movie: '电影',
    Episode: '剧集',
    Series: '系列',
    Season: '季'
  }
  return labelMap[type] || type
}

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

const formatDuration = (seconds: number) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h${m}m`
  return `${m}min`
}

const getLibraryLabel = (lib: MediaServerLibrary) => {
  if (!lib.locations?.length) return lib.name
  return `${lib.name} (${lib.locations.join(', ')})`
}

// ==================== 生命周期 ====================
onMounted(async () => {
  await loadConfigs()
  if (filters.value.config_id) {
    await loadLibraries()
    const queryLibraryId = route.query.library_id as string | undefined
    if (queryLibraryId && libraries.value.some(l => l.id === queryLibraryId)) {
      filters.value.library_id = queryLibraryId
    }
    await Promise.all([loadItems(), loadStatistics()])
  }
  nextTick(() => setupObserver())
})

onUnmounted(() => {
  cleanupObserver()
})
</script>

<style scoped lang="scss">
.media-library-page {
  padding: 20px;
  background: var(--nf-bg-page);
  min-height: 100vh;
}

.filter-bar {
  background: var(--nf-bg-elevated);
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: var(--nf-shadow-sm);

  .filter-form {
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 12px 0;

    :deep(.el-form-item) {
      margin-bottom: 0;
      margin-right: 16px;
    }

    :deep(.el-form-item:last-child) {
      margin-left: auto;
      margin-right: 0;
    }
  }
}

// 面包屑
.breadcrumb-bar {
  background: var(--nf-bg-elevated);
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: var(--nf-shadow-sm);

  .breadcrumb-link {
    cursor: pointer;
    color: var(--el-color-primary);

    &:hover {
      text-decoration: underline;
    }
  }
}

.stats-bar {
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

/* 卡片网格 */
.cards-container {
  min-height: 200px;
}

.media-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: translateY(-4px);

    .poster-image {
      transform: scale(1.06);
    }

    .card-overlay {
      opacity: 1;
    }
  }
}

/* 海报区域 */
.card-poster {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  overflow: hidden;
  background: var(--nf-bg-overlay);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  transition: box-shadow 0.3s;

  .media-card:hover & {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  }
}

.poster-image {
  width: 100%;
  height: 100%;
  transition: transform 0.5s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.poster-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  color: var(--nf-text-placeholder);
  background: var(--nf-bg-overlay);
}

/* 悬浮遮罩 */
.card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.5) 0%,
    transparent 35%,
    transparent 50%,
    rgba(0, 0, 0, 0.7) 100%
  );
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 10px;
  opacity: 0;
  transition: opacity 0.3s;

  &--visible {
    opacity: 1;
    background: linear-gradient(
      to bottom,
      transparent 0%,
      transparent 50%,
      rgba(0, 0, 0, 0.7) 100%
    );
  }
}

.overlay-top {
  display: flex;
  justify-content: flex-start;
}

.type-tag {
  font-size: 11px;
  backdrop-filter: blur(4px);
}

.overlay-bottom {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.overlay-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: white;
}

.meta-year {
  font-size: 13px;
  font-weight: 600;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}

.meta-plays {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0.9;
  color: var(--el-color-success-light-3);

  .el-icon {
    font-size: 13px;
  }
}

.overlay-actions {
  :deep(.el-button) {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
    backdrop-filter: blur(4px);
    transition: all 0.2s;

    &:hover {
      background: var(--el-color-primary);
      border-color: var(--el-color-primary);
      transform: scale(1.1);
    }
  }
}

/* Series 统计角标 */
.series-badge {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px 8px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
  color: white;
  font-size: 11px;
  font-weight: 500;
  text-align: center;
  z-index: 2;
}

/* 卡片底部文字 */
.card-info {
  padding: 8px 2px 0;
}

.card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--nf-text-primary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-subtitle {
  font-size: 11px;
  color: var(--nf-text-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ==================== 剧集信息头 ==================== */
.series-header {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 20px;
  background: var(--nf-bg-elevated);
  border-radius: 8px;
  box-shadow: var(--nf-shadow-sm);
}

.series-header-poster {
  flex-shrink: 0;
  width: 160px;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.series-header-image {
  width: 100%;
  height: 100%;
}

.series-header-info {
  flex: 1;
  min-width: 0;
}

.series-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--nf-text-primary);
  margin: 0 0 4px;
}

.series-original-name {
  font-size: 14px;
  color: var(--nf-text-secondary);
  margin-bottom: 12px;
}

.series-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.series-genres {
  font-size: 13px;
  color: var(--nf-text-secondary);
}

.series-overview {
  font-size: 13px;
  line-height: 1.6;
  color: var(--nf-text-secondary);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ==================== 剧集列表 ==================== */
.episodes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.episode-item {
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  background: var(--nf-bg-elevated);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--nf-shadow-sm);

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    transform: translateX(4px);
  }
}

.episode-thumb {
  flex-shrink: 0;
  width: 200px;
  aspect-ratio: 16 / 9;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  background: var(--nf-bg-overlay);
}

.episode-thumb-image {
  width: 100%;
  height: 100%;
}

.episode-thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--nf-text-placeholder);
}

.episode-duration {
  position: absolute;
  bottom: 4px;
  right: 4px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.75);
  color: white;
  font-size: 11px;
  border-radius: 4px;
}

.episode-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.episode-number {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.episode-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--nf-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.episode-overview {
  font-size: 12px;
  color: var(--nf-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.episode-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 2px;
}

.episode-date {
  font-size: 12px;
  color: var(--nf-text-placeholder);
}

.episode-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* 横版海报卡片 */
.media-card-landscape {
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: translateY(-4px);

    .landscape-poster-image {
      transform: scale(1.06);
    }

    .landscape-overlay {
      opacity: 1;
    }
  }
}

.landscape-poster {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: var(--nf-bg-overlay);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  transition: box-shadow 0.3s;

  .media-card-landscape:hover & {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  }
}

.landscape-poster-image {
  width: 100%;
  height: 100%;
  transition: transform 0.5s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.landscape-poster-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  color: var(--nf-text-placeholder);
  background: var(--nf-bg-overlay);
}

.landscape-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.5) 0%,
    transparent 35%,
    transparent 50%,
    rgba(0, 0, 0, 0.7) 100%
  );
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 10px;
  opacity: 0;
  transition: opacity 0.3s;
}

/* 无限滚动 */
.scroll-trigger {
  height: 1px;
}

.load-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 0;
  font-size: 13px;
  color: var(--nf-text-secondary);

  .el-icon {
    font-size: 18px;
  }

  &--done {
    color: var(--nf-text-placeholder);
  }
}

/* shimmer 骨架 */
.shimmer {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite linear;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

html.dark .shimmer {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite linear;
}

// 同步对话框样式
.sync-mode-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.sync-mode-radio {
  display: flex;
  align-items: flex-start;
  height: auto !important;

  :deep(.el-radio__label) {
    white-space: normal;
    line-height: 1.5;
  }
}

.sync-mode-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sync-mode-title {
  font-weight: 500;
  color: var(--nf-text-primary);
}

.sync-mode-desc {
  font-size: 12px;
  color: var(--nf-text-secondary);
  line-height: 1.4;
}

// 响应式 - 剧集列表在小屏幕上调整
@media (max-width: 768px) {
  .series-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .series-header-poster {
    width: 120px;
  }

  .episode-thumb {
    width: 120px;
  }

  .episode-overview {
    display: none;
  }
}
</style>
