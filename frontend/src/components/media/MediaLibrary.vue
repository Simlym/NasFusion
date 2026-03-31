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

        <el-form-item label="项类型">
          <el-select
            v-model="filters.item_type"
            placeholder="全部"
            clearable
            @change="handleFilterChange"
            style="width: 140px"
          >
            <el-option label="电影" value="Movie" />
            <el-option label="剧集" value="Episode" />
            <el-option label="季" value="Season" />
            <el-option label="系列" value="Series" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词">
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

        <!-- 视图切换 -->
        <el-form-item style="margin-left: auto; margin-right: 0">
          <el-button-group>
            <el-tooltip content="竖版海报" placement="top">
              <el-button
                :type="viewMode === 'portrait' ? 'primary' : 'default'"
                :icon="Grid"
                @click="viewMode = 'portrait'"
              />
            </el-tooltip>
            <el-tooltip content="横版列表" placement="top">
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

    <!-- 统计信息 -->
    <div v-if="statistics" class="stats-bar">
      <el-tag type="info">总计: {{ statistics.total_count || 0 }}</el-tag>
      <el-tag v-if="statistics.by_type?.movie" type="primary">电影: {{ statistics.by_type.movie }}</el-tag>
      <el-tag v-if="statistics.by_type?.tv" type="success">电视剧: {{ statistics.by_type.tv }}</el-tag>
      <el-tag type="warning">已匹配文件: {{ statistics.matched_file_count || 0 }}</el-tag>
      <el-tag type="danger">已匹配资源: {{ statistics.matched_unified_count || 0 }}</el-tag>
    </div>

    <!-- 媒体项卡片网格 -->
    <div v-loading="loading" class="cards-container">
      <el-empty v-if="!loading && items.length === 0" description="暂无媒体项" />

      <!-- 竖版：海报网格 -->
      <el-row v-else-if="viewMode === 'portrait'" :gutter="16">
        <el-col
          v-for="item in items"
          :key="item.id"
          :xs="12" :sm="8" :md="6" :lg="4" :xl="3"
        >
          <div class="media-card" @click="openInMediaServer(item)">
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

              <div class="assoc-badges">
                <el-tooltip v-if="item.media_file_id" content="已关联本地文件" placement="top">
                  <span class="assoc-dot dot-file"></span>
                </el-tooltip>
                <el-tooltip v-if="item.unified_resource_id" content="已关联统一资源" placement="top">
                  <span class="assoc-dot dot-resource"></span>
                </el-tooltip>
              </div>
            </div>

            <div class="card-info">
              <div class="card-title" :title="item.name">{{ item.name }}</div>
              <div v-if="item.original_name && item.original_name !== item.name" class="card-subtitle" :title="item.original_name">
                {{ item.original_name }}
              </div>
              <div v-else-if="item.series_name" class="card-subtitle">
                {{ item.series_name }}
                <span v-if="item.season_number">S{{ String(item.season_number).padStart(2, '0') }}</span>
                <span v-if="item.episode_number">E{{ String(item.episode_number).padStart(2, '0') }}</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 横版：列表卡片 -->
      <el-row v-else :gutter="16">
        <el-col
          v-for="item in items"
          :key="item.id"
          :xs="24" :sm="24" :md="12" :lg="8"
        >
          <div class="media-card-landscape" @click="openInMediaServer(item)">
            <!-- 缩略图 -->
            <div class="landscape-thumb">
              <el-image
                v-if="item.image_url"
                :src="item.image_url"
                fit="cover"
                lazy
                class="thumb-image"
              >
                <template #placeholder>
                  <div class="thumb-placeholder shimmer"></div>
                </template>
                <template #error>
                  <div class="thumb-placeholder">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div v-else class="thumb-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
            </div>

            <!-- 详细信息 -->
            <div class="landscape-info">
              <div class="landscape-title" :title="item.name">{{ item.name }}</div>
              <div v-if="item.original_name && item.original_name !== item.name" class="landscape-original" :title="item.original_name">
                {{ item.original_name }}
              </div>
              <div v-else-if="item.series_name" class="landscape-original">
                {{ item.series_name }}
                <span v-if="item.season_number">S{{ String(item.season_number).padStart(2, '0') }}</span>
                <span v-if="item.episode_number">E{{ String(item.episode_number).padStart(2, '0') }}</span>
              </div>

              <div class="landscape-meta">
                <el-tag size="small" :type="getItemTypeTag(item.item_type)">
                  {{ getItemTypeLabel(item.item_type) }}
                </el-tag>
                <span v-if="item.year" class="meta-text">{{ item.year }}</span>
                <span v-if="item.play_count > 0" class="meta-text plays">
                  <el-icon><VideoPlay /></el-icon>
                  {{ item.play_count }} 次
                </span>
              </div>

              <div v-if="item.date_created" class="landscape-date">
                加入于 {{ formatDate(item.date_created) }}
              </div>

              <div class="landscape-badges">
                <el-tag v-if="item.media_file_id" type="success" size="small">已关联文件</el-tag>
                <el-tag v-if="item.unified_resource_id" type="primary" size="small">已关联资源</el-tag>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div v-if="item.web_url" class="landscape-action">
              <el-button
                type="primary"
                circle
                :icon="VideoPlay"
                @click.stop="openInMediaServer(item)"
              />
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 无限滚动触发点 -->
    <div ref="scrollTrigger" class="scroll-trigger"></div>

    <!-- 加载更多 / 全部加载完 -->
    <div v-if="loadingMore" class="load-status">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中…</span>
    </div>
    <div v-else-if="noMore && items.length > 0" class="load-status load-status--done">
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
  getMediaServerLibraries
} from '@/api/modules/mediaServer'
import type { MediaServerConfig, MediaServerLibrary } from '@/types/mediaServer'

const route = useRoute()

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
  item_type: undefined as string | undefined,
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

// 加载配置列表
const loadConfigs = async () => {
  try {
    const res = await getMediaServerConfigs()
    configs.value = res.data
    // 优先使用路由参数，否则默认选第一个
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

// 加载媒体库列表
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

// 加载媒体项列表
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
      item_type: filters.value.item_type,
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

// 加载统计信息
const loadStatistics = async () => {
  if (!filters.value.config_id) return
  try {
    const res = await getMediaServerLibraryStatistics(filters.value.config_id)
    statistics.value = res.data
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 同步媒体库
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

const handleFilterChange = () => {
  loadItems()
  loadStatistics()
}

const handleServerChange = async () => {
  filters.value.library_id = undefined
  await loadLibraries()
  handleFilterChange()
}

const handleSearchDebounced = debounce(() => {
  handleFilterChange()
}, 500)

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

const getLibraryLabel = (lib: MediaServerLibrary) => {
  if (!lib.locations?.length) return lib.name
  return `${lib.name} (${lib.locations.join(', ')})`
}

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

/* 关联状态角标 */
.assoc-badges {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 2;
}

.assoc-dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.6);

  &.dot-file {
    background: var(--el-color-success);
  }

  &.dot-resource {
    background: var(--el-color-primary);
  }
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

/* 横版列表卡片 */
.media-card-landscape {
  display: flex;
  align-items: stretch;
  gap: 0;
  margin-bottom: 12px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--nf-bg-elevated);
  box-shadow: var(--nf-shadow-sm);
  cursor: pointer;
  transition: transform 0.25s, box-shadow 0.25s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--nf-shadow-md, 0 4px 16px rgba(0, 0, 0, 0.15));

    .thumb-image {
      transform: scale(1.06);
    }
  }
}

.landscape-thumb {
  flex-shrink: 0;
  width: 90px;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  background: var(--nf-bg-overlay);
}

.thumb-image {
  width: 100%;
  height: 100%;
  transition: transform 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--nf-text-placeholder);
  background: var(--nf-bg-overlay);
}

.landscape-info {
  flex: 1;
  min-width: 0;
  padding: 12px 12px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.landscape-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--nf-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.landscape-original {
  font-size: 12px;
  color: var(--nf-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.landscape-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 2px;
}

.meta-text {
  font-size: 12px;
  color: var(--nf-text-secondary);

  &.plays {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    color: var(--el-color-success);

    .el-icon {
      font-size: 13px;
    }
  }
}

.landscape-date {
  font-size: 11px;
  color: var(--nf-text-placeholder);
}

.landscape-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: auto;
}

.landscape-action {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 14px;
  opacity: 0;
  transition: opacity 0.2s;

  .media-card-landscape:hover & {
    opacity: 1;
  }
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
</style>
