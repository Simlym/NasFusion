<template>
  <div class="watch-history-view">
    <!-- 筛选工具栏 -->
    <div class="filter-toolbar">
      <div class="filter-left">
        <div class="filter-group">
          <span class="filter-label">服务器</span>
          <el-select v-model="filters.config_id" placeholder="全部" clearable class="filter-select" @change="handleFilterChange">
            <template #prefix>
              <el-icon><Monitor /></el-icon>
            </template>
            <el-option v-for="config in configs" :key="config.id" :label="config.name" :value="config.id" />
          </el-select>
        </div>
        
        <div class="filter-group">
          <span class="filter-label">类型</span>
          <el-select v-model="filters.media_type" placeholder="全部" clearable class="filter-select" @change="handleFilterChange">
            <template #prefix>
              <el-icon><VideoCamera /></el-icon>
            </template>
            <el-option label="电影" value="movie" />
            <el-option label="剧集" value="tv" />
          </el-select>
        </div>

        <el-checkbox v-model="filters.is_completed" class="filter-checkbox" @change="handleFilterChange">
          仅显示已看完
        </el-checkbox>
      </div>
      <div class="filter-right">
        <el-button
          v-if="filters.config_id"
          :icon="Refresh"
          :loading="syncing"
          class="ml-2"
          @click="handleSync"
        >
          同步观看历史
        </el-button>
        <!-- <el-button :icon="Refresh" @click="handleRefresh">刷新</el-button> -->
      </div>
    </div>

    <!-- 历史列表 -->
    <div v-loading="loading && history.length === 0" class="history-grid">
      <WatchHistoryItem 
        v-for="item in history" 
        :key="item.id" 
        :history="item" 
      />
    </div>

    <!-- 注意：显示设置对话框已移至 MediaServerOverview 组件 -->

    <!-- 加载更多触发器 -->
    <div v-if="history.length > 0" ref="loadMoreTrigger" class="load-more-trigger">
      <span v-if="loadingMore"><el-icon class="is-loading"><Loading /></el-icon> 正在加载更多...</span>
      <span v-else-if="noMore">没有更多记录了</span>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && history.length === 0" description="暂无观看历史">
      <p class="empty-tip">请确保已在设置中启用媒体服务器的历史同步功能</p>
      <el-button type="primary" @click="goToSettings">前往设置</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Loading } from '@element-plus/icons-vue'
import api from '@/api'
import type { ViewingHistory, MediaServerConfig } from '@/types/mediaServer'
import WatchHistoryItem from './WatchHistoryItem.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()

const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const syncing = ref(false)
const history = ref<ViewingHistory[]>([])
const configs = ref<MediaServerConfig[]>([])
const loadMoreTrigger = ref<HTMLElement | null>(null)

const filters = reactive({
  config_id: undefined as number | undefined,
  media_type: undefined as string | undefined,
  is_completed: false,
  page: 1,
  page_size: 24
})

let observer: IntersectionObserver | null = null

const loadConfigs = async () => {
  try {
    const res = await api.mediaServer.getMediaServerConfigs()
    configs.value = res.data

    // 默认选择第一个服务器
    if (configs.value.length > 0 && !filters.config_id) {
      filters.config_id = configs.value[0].id
    }
  } catch (err) {
    console.error('Failed to load configs:', err)
  }
}

const loadHistory = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
    filters.page = 1
  }

  try {
    const res = await api.mediaServer.getWatchHistory({
      ...filters,
      is_completed: filters.is_completed || undefined // 只有在勾选时传递true
    })
    
    if (append) {
      history.value = [...history.value, ...res.data.items]
    } else {
      history.value = res.data.items
    }
    
    noMore.value = history.value.length >= res.data.total
  } catch (err) {
    ElMessage.error('加载观看历史失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const handleFilterChange = () => {
  loadHistory()
}

const handleRefresh = () => {
  loadHistory()
}

const handleSync = async () => {
  if (!filters.config_id) {
    ElMessage.warning('请先选择媒体服务器')
    return
  }

  syncing.value = true
  try {
    const res = await api.mediaServer.syncWatchHistory(filters.config_id)
    ElMessage.success(`同步完成，新增 ${res.data.new_count} 条记录`)
    // 刷新列表
    await loadHistory()
  } catch (err) {
    ElMessage.error('同步失败')
  } finally {
    syncing.value = false
  }
}

const handleLoadMore = () => {
  if (loadingMore.value || noMore.value) return
  filters.page++
  loadHistory(true)
}

const setupObserver = () => {
  if (!loadMoreTrigger.value) return
  
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      handleLoadMore()
    }
  }, { threshold: 0.1 })
  
  observer.observe(loadMoreTrigger.value)
}

const goToSettings = () => {
  router.push({ name: 'Settings', query: { tab: 'media-servers' } })
}

onMounted(async () => {
  await loadConfigs()
  await loadHistory()
  nextTick(() => {
    setupObserver()
  })
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})
</script>

<style scoped>
.watch-history-view {
  padding: 8px 24px;
}

/* ====== 工具栏 ====== */
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.filter-select {
  width: 140px;
}

.filter-checkbox {
  margin-right: 0;
}

/* ====== 网格 ====== */
.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.load-more-trigger {
  text-align: center;
  padding: 28px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.empty-tip {
  color: var(--el-text-color-secondary);
  margin-bottom: 20px;
}

/* ====== 响应式 ====== */
@media (max-width: 768px) {
  .watch-history-view {
    padding: 12px;
  }

  .history-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
