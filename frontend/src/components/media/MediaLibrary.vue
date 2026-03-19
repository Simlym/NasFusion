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

    <!-- 媒体项列表 -->
    <el-table
      v-loading="loading"
      :data="items"
      style="width: 100%"
      stripe
      :height="tableHeight"
      @sort-change="handleSortChange"
    >
      <el-table-column label="海报" width="80" align="center">
        <template #default="scope">
          <el-image
            v-if="scope.row.image_url"
            :src="scope.row.image_url"
            fit="cover"
            style="width: 50px; height: 75px; border-radius: 4px"
            lazy
          >
            <template #error>
              <div class="image-slot">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          <div v-else class="image-slot">
            <el-icon><Picture /></el-icon>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="标题" min-width="250" show-overflow-tooltip>
        <template #default="scope">
          <div class="title-cell">
            <div class="title-main">{{ scope.row.name }}</div>
            <div v-if="scope.row.original_name && scope.row.original_name !== scope.row.name" class="title-sub">
              {{ scope.row.original_name }}
            </div>
            <div v-if="scope.row.series_name" class="title-sub">
              {{ scope.row.series_name }}
              <span v-if="scope.row.season_number">S{{ String(scope.row.season_number).padStart(2, '0') }}</span>
              <span v-if="scope.row.episode_number">E{{ String(scope.row.episode_number).padStart(2, '0') }}</span>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="类型" width="100" align="center">
        <template #default="scope">
          <el-tag size="small" :type="getItemTypeTag(scope.row.item_type)">
            {{ scope.row.item_type }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="年份" width="80" align="center" sortable="custom" prop="year">
        <template #default="scope">
          {{ scope.row.year || '-' }}
        </template>
      </el-table-column>

      <el-table-column label="加入时间" width="160" sortable="custom" prop="date_created">
        <template #default="scope">
          {{ scope.row.date_created ? formatDate(scope.row.date_created) : '-' }}
        </template>
      </el-table-column>

      <el-table-column label="播放次数" width="120" align="center" sortable="custom" prop="play_count">
        <template #default="scope">
          <el-tag v-if="scope.row.play_count > 0" type="success" size="small">
            {{ scope.row.play_count }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column label="最后播放" width="160" sortable="custom" prop="last_played_at">
        <template #default="scope">
          {{ scope.row.last_played_at ? formatDate(scope.row.last_played_at) : '-' }}
        </template>
      </el-table-column>

      <el-table-column label="关联状态" width="120" align="center">
        <template #default="scope">
          <div class="association-status">
            <el-tooltip content="已关联本地文件" placement="top">
              <el-tag v-if="scope.row.media_file_id" type="success" size="small" :icon="Document">文件</el-tag>
            </el-tooltip>
            <el-tooltip content="已关联统一资源" placement="top">
              <el-tag v-if="scope.row.unified_resource_id" type="primary" size="small" :icon="Link">资源</el-tag>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="180" align="center" fixed="right">
        <template #default="scope">
          <el-button
            v-if="scope.row.web_url"
            type="primary"
            size="small"
            link
            @click="openInJellyfin(scope.row)"
          >
            <el-icon class="el-icon--left"><VideoPlay /></el-icon>
            在 Jellyfin 中播放
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :page-sizes="[20, 50, 100, 200]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
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
import { ref, onMounted, computed } from 'vue'
import { Search, Refresh, Connection, Picture, Document, Link, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { debounce } from 'lodash-es'
import {
  getMediaServerConfigs,
  getMediaServerLibraryItems,
  syncMediaServerLibrary,
  getMediaServerLibraryStatistics,
  getMediaServerLibraries
} from '@/api/modules/mediaServer'
import type { MediaServerConfig, MediaServerLibrary } from '@/types/mediaServer'

const configs = ref<MediaServerConfig[]>([])
const libraries = ref<MediaServerLibrary[]>([])
const items = ref<any[]>([])
const statistics = ref<any>(null)
const loading = ref(false)
const syncing = ref(false)

const filters = ref({
  config_id: undefined as number | undefined,
  library_id: undefined as string | undefined,
  media_type: undefined as string | undefined,
  item_type: undefined as string | undefined,
  keyword: ''
})

const pagination = ref({
  page: 1,
  page_size: 100,
  total: 0
})

const sortField = ref('synced_at')
const sortOrder = ref(true) // true = desc

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

// 加载配置列表
const loadConfigs = async () => {
  try {
    const res = await getMediaServerConfigs()
    configs.value = res.data

    // 默认选择第一个
    if (configs.value.length > 0 && !filters.value.config_id) {
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
const loadItems = async () => {
  if (!filters.value.config_id) {
    items.value = []
    pagination.value.total = 0
    return
  }

  loading.value = true
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

    items.value = res.data.items
    pagination.value.total = res.data.total
  } catch (error: any) {
    console.error('加载媒体项失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
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

    // 3秒后刷新列表
    setTimeout(() => {
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

// 筛选变化
const handleFilterChange = () => {
  pagination.value.page = 1
  loadItems()
  loadStatistics()
}

// 服务器切换
const handleServerChange = async () => {
  // 清空媒体库选择
  filters.value.library_id = undefined
  
  // 加载新服务器的媒体库列表
  await loadLibraries()
  
  // 触发筛选变化
  handleFilterChange()
}

// 搜索防抖
const handleSearchDebounced = debounce(() => {
  handleFilterChange()
}, 500)

// 排序变化
const handleSortChange = ({ prop, order }: any) => {
  if (prop) {
    sortField.value = prop
    sortOrder.value = order === 'descending'
    loadItems()
  }
}

// 分页变化
const handlePageChange = () => {
  loadItems()
}

const handleSizeChange = () => {
  pagination.value.page = 1
  loadItems()
}

// 在 Jellyfin 中打开
const openInJellyfin = (item: any) => {
  if (item.web_url) {
    window.open(item.web_url, '_blank')
  }
}

// 获取项类型标签颜色
const getItemTypeTag = (type: string) => {
  const typeMap: Record<string, any> = {
    Movie: 'primary',
    Episode: 'success',
    Series: 'info',
    Season: 'warning'
  }
  return typeMap[type] || ''
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

// 媒体库显示标签（名称 + 目录路径）
const getLibraryLabel = (lib: MediaServerLibrary) => {
  if (!lib.locations?.length) return lib.name
  return `${lib.name} (${lib.locations.join(', ')})`
}

onMounted(async () => {
  await loadConfigs()
  if (filters.value.config_id) {
    await loadLibraries()
    await Promise.all([loadItems(), loadStatistics()])
  }
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
}

.title-cell {
  .title-main {
    font-weight: 500;
    color: var(--nf-text-primary);
    margin-bottom: 4px;
  }

  .title-sub {
    font-size: 12px;
    color: var(--nf-text-secondary);
  }
}

.association-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.image-slot {
  width: 50px;
  height: 75px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--nf-bg-overlay);
  border-radius: 4px;
  color: var(--nf-text-placeholder);
  font-size: 24px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  background: var(--nf-bg-elevated);
  padding: 20px;
  border-radius: 8px;
  box-shadow: var(--nf-shadow-sm);
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
