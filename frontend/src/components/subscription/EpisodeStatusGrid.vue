<template>
  <div class="episode-status-grid">
    <div class="grid-header">
      <div class="header-left">
        <div class="title-row">
          <h3>集数状态</h3>
          <el-tag size="small" effect="plain" round type="info">第 {{ season }} 季</el-tag>
          <span class="total-count">共 {{ totalEpisodes }} 集</span>
        </div>
      </div>
      <div class="header-right">
        <el-button
          :icon="Refresh"
          :loading="refreshing"
          link
          type="primary"
          class="refresh-btn"
          @click="handleRefresh"
        >
          刷新状态
        </el-button>
      </div>
    </div>

    <!-- 状态图例与统计 -->
    <div class="status-legend">
      <div class="legend-item downloaded">
        <div class="square-icon"></div>
        <span class="label">已下载</span>
        <span class="count">{{ stats?.downloaded || 0 }}</span>
      </div>
      <div class="legend-item downloading">
        <div class="square-icon"></div>
        <span class="label">下载中</span>
        <span class="count">{{ stats?.downloading || 0 }}</span>
      </div>
      <div class="legend-item available">
        <div class="square-icon"></div>
        <span class="label">可下载</span>
        <span class="count">{{ stats?.available || 0 }}</span>
      </div>
      <div class="legend-item waiting">
        <div class="square-icon"></div>
        <span class="label">等待中</span>
        <span class="count">{{ stats?.waiting || 0 }}</span>
      </div>
      <div v-if="stats?.failed && stats.failed > 0" class="legend-item failed">
        <div class="square-icon"></div>
        <span class="label">失败</span>
        <span class="count">{{ stats.failed }}</span>
      </div>
      <div v-if="stats?.ignored && stats.ignored > 0" class="legend-item ignored">
        <div class="square-icon"></div>
        <span class="label">已忽略</span>
        <span class="count">{{ stats.ignored }}</span>
      </div>
    </div>

    <div v-loading="loading" class="episodes-container">
      <el-tooltip
        v-for="episode in episodeList"
        :key="episode.number"
        placement="top"
        :show-after="200"
        :offset="12"
        effect="light"
        popper-class="episode-tooltip"
      >
        <template #content>
          <div class="tooltip-content">
            <div class="tooltip-header">
              <span class="tooltip-title">第 {{ episode.number }} 集</span>
              <el-tag size="small" :type="getStatusTagType(episode.status)" effect="dark" class="status-tag">
                {{ getStatusText(episode.status) }}
              </el-tag>
            </div>
            
            <div class="tooltip-divider"></div>

            <div class="tooltip-details">
              <div v-if="episode.quality" class="detail-row">
                <span class="detail-label">最佳质量</span>
                <span class="detail-value">{{ episode.quality }}</span>
              </div>
              <div v-if="episode.status === 'downloading' && episode.progress !== undefined" class="detail-row">
                <span class="detail-label">下载进度</span>
                <span class="detail-value highlight">{{ episode.progress }}%</span>
              </div>
              <div v-if="episode.resourceCount" class="detail-row">
                <span class="detail-label">可用资源</span>
                <span class="detail-value">{{ episode.resourceCount }} 个</span>
              </div>
              <div v-if="episode.fileSize" class="detail-row">
                <span class="detail-label">文件大小</span>
                <span class="detail-value">{{ formatSize(episode.fileSize) }}</span>
              </div>
              <div v-if="episode.downloadedAt" class="detail-row">
                <span class="detail-label">完成时间</span>
                <span class="detail-value">{{ formatTime(episode.downloadedAt) }}</span>
              </div>
              <div v-else-if="episode.foundAt && episode.status === 'available'" class="detail-row">
                <span class="detail-label">发现时间</span>
                <span class="detail-value">{{ formatTime(episode.foundAt) }}</span>
              </div>
              <div v-if="episode.airDate" class="detail-row">
                <span class="detail-label">首播日期</span>
                <span class="detail-value">{{ episode.airDate }}</span>
              </div>
              <div v-if="episode.checkedAt" class="detail-row">
                <span class="detail-label">最后检查</span>
                <span class="detail-value">{{ formatTime(episode.checkedAt) }}</span>
              </div>
              <div v-if="!episode.quality && !episode.resourceCount && !episode.fileSize && !episode.airDate && !episode.checkedAt" class="detail-row">
                <span class="detail-label">暂无详细记录</span>
              </div>
            </div>
            <div class="tooltip-footer">
              <div class="hint-item">
                <el-icon><Pointer /></el-icon>
                <span>点击筛选资源</span>
              </div>
              <div class="hint-item">
                <el-icon><Mouse /></el-icon>
                <span>右键标记状态</span>
              </div>
            </div>
          </div>
        </template>

        <div
          :class="['episode-box', `status-${episode.status}`]"
          @click="handleEpisodeClick(episode)"
          @contextmenu.prevent="handleContextMenu($event, episode)"
        >
          <span class="episode-num">{{ episode.number }}</span>
          <div v-if="episode.status === 'downloading'" class="progress-bar" :style="{ height: episode.progress + '%' }"></div>
        </div>
      </el-tooltip>
    </div>

    <!-- 右键菜单 -->
    <teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="episode-context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <div
          v-if="contextMenu.episode?.status !== 'downloaded'"
          class="menu-item downloaded"
          @click="handleMarkStatus('downloaded')"
        >
          标记为已下载
        </div>
        <div
          v-if="contextMenu.episode?.status !== 'ignored'"
          class="menu-item ignored"
          @click="handleMarkStatus('ignored')"
        >
          标记为忽略
        </div>
        <div
          v-if="contextMenu.episode?.status !== 'waiting'"
          class="menu-item waiting"
          @click="handleMarkStatus('waiting')"
        >
          重置为等待中
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Refresh, Pointer, Mouse } from '@element-plus/icons-vue'

interface EpisodeStatus {
  number: number
  title?: string
  status: string
  quality?: string
  fileSize?: number
  filePath?: string
  progress?: number
  resourceCount?: number
  qualities?: string[]
  downloadedAt?: string
  startedAt?: string
  foundAt?: string
  checkedAt?: string
  airDate?: string
}

interface Props {
  episodes: Record<string, any>
  stats: {
    total: number
    downloaded: number
    downloading: number
    available: number
    waiting: number
    failed: number
    ignored?: number
  }
  season: number
  totalEpisodes: number
  startEpisode?: number
  loading?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  refresh: []
  'view-resources': [episode: number]
  'search-episode': [episode: number]
  'mark-status': [episode: number, status: string]
}>()

const refreshing = ref(false)

// 右键菜单状态
const contextMenu = ref<{
  visible: boolean
  x: number
  y: number
  episode: EpisodeStatus | null
}>({
  visible: false,
  x: 0,
  y: 0,
  episode: null,
})

const handleContextMenu = (event: MouseEvent, episode: EpisodeStatus) => {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    episode,
  }
}

const handleMarkStatus = (status: string) => {
  if (contextMenu.value.episode) {
    emit('mark-status', contextMenu.value.episode.number, status)
  }
  contextMenu.value.visible = false
}

const closeContextMenu = () => {
  contextMenu.value.visible = false
}

onMounted(() => {
  document.addEventListener('click', closeContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', closeContextMenu)
})

// 转换为数组格式便于展示
const episodeList = computed(() => {
  const list: EpisodeStatus[] = []
  let maxEpisode = props.totalEpisodes
  if (maxEpisode === 0 && props.episodes) {
    const keys = Object.keys(props.episodes).map(Number)
    if (keys.length > 0) maxEpisode = Math.max(...keys)
  }
  
  const start = props.startEpisode || 1

  for (let i = start; i <= maxEpisode; i++) {
    const episodeData = props.episodes[i.toString()]
    list.push({
      number: i,
      title: episodeData?.title,
      status: episodeData?.status || 'waiting',
      quality: episodeData?.quality || episodeData?.bestQuality,
      fileSize: episodeData?.fileSize || episodeData?.file_size,
      filePath: episodeData?.filePath || episodeData?.file_path,
      progress: episodeData?.progress,
      resourceCount: episodeData?.resourceCount || episodeData?.resource_count,
      qualities: episodeData?.qualities,
      downloadedAt: episodeData?.downloadedAt || episodeData?.downloaded_at,
      startedAt: episodeData?.startedAt || episodeData?.started_at,
      foundAt: episodeData?.foundAt || episodeData?.found_at,
      checkedAt: episodeData?.checkedAt || episodeData?.checked_at,
      airDate: episodeData?.airDate || episodeData?.air_date
    })
  }
  return list
})

// 刷新状态
const handleRefresh = async () => {
  refreshing.value = true
  try {
    emit('refresh')
  } finally {
    setTimeout(() => {
      refreshing.value = false
    }, 1000)
  }
}

// 点击集数 - 直接筛选资源
const handleEpisodeClick = (episode: EpisodeStatus) => {
  emit('view-resources', episode.number)
}

// 获取状态文本
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    downloaded: '已下载',
    downloading: '下载中',
    available: '可下载',
    waiting: '等待中',
    failed: '下载失败',
    ignored: '已忽略',
  }
  return map[status] || status
}

// 获取状态标签类型
const getStatusTagType = (status: string): 'success' | 'primary' | 'warning' | 'info' | 'danger' => {
  const map: Record<string, 'success' | 'primary' | 'warning' | 'info' | 'danger'> = {
    downloaded: 'success',
    downloading: 'primary',
    available: 'warning',
    waiting: 'info',
    failed: 'danger',
    ignored: 'info',
  }
  return map[status] || 'info'
}

// 格式化大小
const formatSize = (bytes: number) => {
  if (!bytes) return '-'
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 格式化时间
const formatTime = (dateString?: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.episode-status-grid {
  width: 100%;
}

.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.grid-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.total-count {
  color: var(--text-color-secondary);
  font-size: 13px;
}

/* 状态图例 */
.status-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 20px;
  padding: 10px 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.legend-item .square-icon {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item .label {
  color: var(--text-color-regular);
}

.legend-item .count {
  background: var(--bg-color-overlay);
  padding: 0px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

/* 状态颜色定义 - 使用 CSS 变量 */
.legend-item.downloaded .square-icon { background-color: var(--success-color); }
.legend-item.downloading .square-icon { background-color: var(--primary-color); }
.legend-item.available .square-icon { background-color: var(--warning-color); }
.legend-item.waiting .square-icon { background-color: var(--border-color); }
.legend-item.failed .square-icon { background-color: var(--danger-color); }
.legend-item.ignored .square-icon { background-color: #909399; }

/* 网格容器 */
.episodes-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px; /* 紧凑间距 */
}

/* 集数方块 - 极简风格 */
.episode-box {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--bg-color-light);
  border: 1px solid var(--border-color-light);
  color: var(--text-color-secondary);
  font-size: 15px;
  font-weight: 500;
  position: relative;
  overflow: hidden;
}

.episode-box:hover {
  transform: translateY(-2px);
  border-color: var(--primary-color);
  box-shadow: var(--box-shadow-md);
  z-index: 1;
}

.progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background-color: rgba(59, 130, 246, 0.2);
  transition: height 0.3s ease;
  pointer-events: none;
}

/* 已下载 */
.episode-box.status-downloaded {
  background-color: #ECFDF5;
  border-color: #D1FAE5;
  color: var(--success-color);
}
html.dark .episode-box.status-downloaded {
  background-color: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
}

.episode-box.status-downloaded:hover {
  background-color: #D1FAE5;
}

/* 下载中 */
.episode-box.status-downloading {
  background-color: #EFF6FF;
  border-color: #DBEAFE;
  color: var(--primary-color);
  font-weight: 600;
}
html.dark .episode-box.status-downloading {
  background-color: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.2);
}

.episode-box.status-downloading:hover {
  background-color: #DBEAFE;
}

/* 可下载 */
.episode-box.status-available {
  background-color: #FFFBEB;
  border-color: #FEF3C7;
  color: var(--warning-color);
}
html.dark .episode-box.status-available {
  background-color: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
}

.episode-box.status-available:hover {
  background-color: #FEF3C7;
}

/* 等待中 */
.episode-box.status-waiting {
  background-color: var(--bg-color-light);
  color: var(--text-color-muted);
}

.episode-box.status-waiting:hover {
  background-color: var(--bg-color-sidebar-hover);
  color: var(--text-color-secondary);
}

/* 失败 */
.episode-box.status-failed {
  background-color: #FEF2F2;
  border-color: #FEE2E2;
  color: var(--danger-color);
}
html.dark .episode-box.status-failed {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
}

/* 已忽略 */
.episode-box.status-ignored {
  background-color: var(--bg-color-light);
  color: var(--text-color-muted);
  text-decoration: line-through;
  opacity: 0.6;
}

/* 覆盖 Element UI 样式 */
:deep(.el-icon) {
  font-size: 14px;
}
</style>

<style>
/* Tooltip 样式 */
.episode-tooltip {
  padding: 0 !important;
  border: 1px solid var(--border-color) !important;
  box-shadow: var(--box-shadow-lg) !important;
  background-color: var(--bg-color-light) !important;
  border-radius: var(--border-radius-md) !important;
}

.tooltip-content {
  padding: 12px 16px;
  min-width: 200px;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tooltip-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.status-tag {
  font-weight: 500;
  border: none;
}

.tooltip-divider {
  height: 1px;
  background: var(--border-color-light);
  margin: 8px 0;
}

.tooltip-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tooltip-details .detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.detail-label {
  color: var(--text-color-secondary);
}

.detail-value {
  color: var(--text-color-regular);
  font-weight: 500;
}

.detail-value.highlight {
  color: var(--primary-color);
  font-weight: 600;
}

.tooltip-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-color-light);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-color-muted);
}

.hint-item .el-icon {
  font-size: 12px;
}

/* 右键菜单 */
.episode-context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-color-overlay, #fff);
  border: 1px solid var(--border-color, #dcdfe6);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 4px 0;
  min-width: 140px;
}

.episode-context-menu .menu-item {
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-color-regular, #606266);
  transition: background-color 0.15s;
}

.episode-context-menu .menu-item:hover {
  background-color: var(--bg-color-page, #f5f7fa);
}

.episode-context-menu .menu-item.downloaded:hover {
  color: var(--success-color, #10b981);
}

.episode-context-menu .menu-item.ignored:hover {
  color: #909399;
}

.episode-context-menu .menu-item.waiting:hover {
  color: var(--primary-color, #3b82f6);
}
</style>
