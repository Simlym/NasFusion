<template>
  <div v-loading="loading" class="episode-detail">
    <template v-if="fileData">

      <!-- 缩略图 + 基本信息 -->
      <div class="hero">
        <!-- 缩略图区域 -->
        <div class="thumb-wrapper">
          <el-image
            v-if="metadata?.poster_url"
            :src="metadata.poster_url"
            fit="cover"
            class="thumb-image"
            :preview-src-list="[metadata.poster_url]"
          >
            <template #error>
              <div class="thumb-placeholder">
                <span class="ep-num-large">
                  {{ fileData.episode_number != null ? `E${String(fileData.episode_number).padStart(2, '0')}` : 'EP' }}
                </span>
              </div>
            </template>
          </el-image>
          <div v-else class="thumb-placeholder">
            <span class="ep-num-large">
              {{ fileData.episode_number != null ? `E${String(fileData.episode_number).padStart(2, '0')}` : 'EP' }}
            </span>
          </div>
        </div>

        <!-- 标题 + 元信息 -->
        <div class="hero-info">
          <div class="ep-badge-row">
            <span class="ep-badge" v-if="fileData.episode_number != null">
              E{{ String(fileData.episode_number).padStart(2, '0') }}
            </span>
            <el-tag v-if="fileData.resolution" size="small" type="info" effect="plain">
              {{ fileData.resolution }}
            </el-tag>
            <el-tag v-if="metadata?.video_codec" size="small" type="info" effect="plain">
              {{ metadata.video_codec }}
            </el-tag>
            <el-tag size="small" :type="metadata?.has_nfo ? 'success' : 'danger'" effect="plain">
              NFO
            </el-tag>
            <el-tag size="small" :type="metadata?.has_poster ? 'success' : 'warning'" effect="plain">
              图片
            </el-tag>
            <el-tag v-if="fileData.has_subtitle" size="small" type="success" effect="plain">
              字幕
            </el-tag>
            <el-tag v-if="metadata?.organized" size="small" type="success" effect="plain">
              已整理
            </el-tag>
            <el-tag v-else size="small" type="info" effect="plain">
              未整理
            </el-tag>
          </div>

          <!-- 集标题 -->
          <h2 class="ep-title">
            {{ nfoTitle || fileData.episode_title || fileData.file_name }}
          </h2>

          <!-- 副标题 -->
          <p v-if="metadata?.sub_title" class="ep-subtitle">{{ metadata.sub_title }}</p>

          <!-- 播出日期 + 评分 + 时长 -->
          <div class="ep-meta-row" v-if="nfoAired || nfoRating || metadata?.duration">
            <span v-if="nfoAired" class="meta-item">
              <el-icon><Calendar /></el-icon> {{ nfoAired }}
            </span>
            <span v-if="nfoRating" class="rating-inline">
              ★ {{ Number(nfoRating).toFixed(1) }}
            </span>
            <span v-if="metadata?.duration" class="meta-item">
              <el-icon><Timer /></el-icon> {{ formatDuration(metadata.duration) }}
            </span>
          </div>

          <!-- 剧情简介 -->
          <p v-if="nfoPlot" class="ep-plot">{{ nfoPlot }}</p>
          <p v-else-if="!loading" class="ep-plot ep-plot--empty">暂无简介</p>
        </div>
      </div>

      <!-- 刮削操作 -->
      <div class="action-bar">
        <el-button
          type="primary"
          size="small"
          :loading="scraping"
          :icon="Refresh"
          @click="handleScrape"
        >
          重新刮削
        </el-button>
        <el-button
          size="small"
          :loading="generating"
          :icon="Document"
          @click="handleGenerateNFO"
        >
          仅生成 NFO
        </el-button>
        <span class="action-hint">强制覆盖已有图片和 NFO</span>
      </div>

      <!-- 文件路径信息 -->
      <div class="info-section">
        <div class="info-section-title">
          <el-icon><Folder /></el-icon>
          <span>文件路径</span>
        </div>
        <div class="path-list">
          <div class="path-item">
            <span class="path-label">原始路径</span>
            <span class="path-value mono">{{ metadata?.file_path || '-' }}</span>
          </div>
          <div v-if="metadata?.organized_path" class="path-item">
            <span class="path-label">整理路径</span>
            <div class="path-value-row">
              <span class="path-value mono">{{ metadata.organized_path }}</span>
              <el-tag v-if="metadata.organize_mode" size="small" type="info" effect="plain">
                {{ metadata.organize_mode }}
              </el-tag>
            </div>
          </div>
          <div class="path-item">
            <span class="path-label">NFO 文件</span>
            <span class="path-value mono" :class="{ 'path-missing': !metadata?.nfo_path }">
              {{ metadata?.nfo_path || '未生成' }}
            </span>
          </div>
          <div class="path-item">
            <span class="path-label">缩略图</span>
            <span class="path-value mono" :class="{ 'path-missing': !metadata?.poster_file_path }">
              {{ metadata?.poster_file_path || '未下载' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 文件详细信息 -->
      <div class="info-section">
        <div class="info-section-title">
          <el-icon><Document /></el-icon>
          <span>文件信息</span>
        </div>
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="文件名" :span="2">
            <span class="mono">{{ fileData.file_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="大小">{{ formatFileSize(fileData.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="分辨率">{{ fileData.resolution || '-' }}</el-descriptions-item>
          <el-descriptions-item label="视频编码">{{ metadata?.video_codec || '-' }}</el-descriptions-item>
          <el-descriptions-item label="时长">{{ metadata?.duration ? formatDuration(metadata.duration) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="集数">
            {{ fileData.episode_number != null ? `第 ${fileData.episode_number} 集` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="集标题">{{ fileData.episode_title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusTagType(metadata?.status)">{{ statusLabel(metadata?.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="媒体类型">{{ mediaTypeLabel(metadata?.media_type) }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- NFO 详细内容（如果存在） -->
      <div v-if="metadata?.nfo_data && Object.keys(metadata.nfo_data).length > 0" class="info-section">
        <div class="info-section-title">
          <el-icon><Tickets /></el-icon>
          <span>NFO 元数据</span>
        </div>
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item v-if="metadata.nfo_data.title" label="标题" :span="2">
            {{ metadata.nfo_data.title }}
          </el-descriptions-item>
          <el-descriptions-item v-if="metadata.nfo_data.originaltitle" label="原始标题" :span="2">
            {{ metadata.nfo_data.originaltitle }}
          </el-descriptions-item>
          <el-descriptions-item v-if="metadata.nfo_data.aired" label="播出日期">
            {{ metadata.nfo_data.aired }}
          </el-descriptions-item>
          <el-descriptions-item v-if="metadata.nfo_data.rating" label="评分">
            ★ {{ Number(metadata.nfo_data.rating).toFixed(1) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="metadata.nfo_data.director" label="导演">
            {{ metadata.nfo_data.director }}
          </el-descriptions-item>
          <el-descriptions-item v-if="metadata.nfo_data.studio" label="制作公司">
            {{ metadata.nfo_data.studio }}
          </el-descriptions-item>
          <el-descriptions-item v-if="metadata.nfo_data.plot" label="简介" :span="2">
            <span class="nfo-plot-text">{{ metadata.nfo_data.plot }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

    </template>

    <el-empty v-else description="请从左侧选择一集" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Document, Calendar, Timer, Folder, Tickets } from '@element-plus/icons-vue'
import { scrapeMediaFile, generateNFO, getEpisodeMetadata, type EpisodeMetadata } from '@/api/modules/media'
import type { EpisodeTreeNode } from './DirectoryTree.vue'

interface Props {
  episode: EpisodeTreeNode | null
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'scrape-done'): void }>()

const loading = ref(false)
const scraping = ref(false)
const generating = ref(false)

const fileData = ref<EpisodeTreeNode | null>(null)
const metadata = ref<EpisodeMetadata | null>(null)

// NFO 字段快捷访问
const nfoTitle = computed(() => metadata.value?.nfo_data?.title || null)
const nfoPlot = computed(() => metadata.value?.nfo_data?.plot || metadata.value?.nfo_data?.outline || null)
const nfoRating = computed(() => metadata.value?.nfo_data?.rating || null)
const nfoAired = computed(() =>
  metadata.value?.nfo_data?.aired
  || metadata.value?.nfo_data?.premiered
  || metadata.value?.nfo_data?.releasedate
  || null
)

const loadMetadata = async () => {
  if (!props.episode) {
    fileData.value = null
    metadata.value = null
    return
  }
  fileData.value = { ...props.episode }
  metadata.value = null
  loading.value = true
  try {
    const res = await getEpisodeMetadata(props.episode.id)
    metadata.value = res.data
    // 同步状态到 fileData 以保持一致
    fileData.value = {
      ...fileData.value,
      has_nfo: res.data.has_nfo,
      has_poster: res.data.has_poster,
    }
  } catch {
    // 静默失败，用树节点数据兜底
  } finally {
    loading.value = false
  }
}

async function handleScrape() {
  if (!fileData.value) return
  scraping.value = true
  try {
    const res = await scrapeMediaFile(fileData.value.id, undefined, true)
    if (res.data.success) {
      ElMessage.success('刮削成功')
      await loadMetadata()
      emit('scrape-done')
    } else {
      ElMessage.error(res.data.error || '刮削失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '刮削失败')
  } finally {
    scraping.value = false
  }
}

async function handleGenerateNFO() {
  if (!fileData.value) return
  generating.value = true
  try {
    const res = await generateNFO(fileData.value.id, undefined, true)
    if (res.data.success) {
      ElMessage.success('NFO 生成成功')
      await loadMetadata()
      emit('scrape-done')
    } else {
      ElMessage.error(res.data.error || 'NFO 生成失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'NFO 生成失败')
  } finally {
    generating.value = false
  }
}

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '-'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i]
}

const formatDuration = (seconds: number): string => {
  if (!seconds) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

const statusLabel = (status?: string | null): string => {
  const map: Record<string, string> = {
    discovered: '已发现',
    identifying: '识别中',
    identified: '已识别',
    organizing: '整理中',
    scraping: '刮削中',
    completed: '已完成',
    failed: '失败',
    ignored: '已忽略',
  }
  return map[status || ''] || status || '-'
}

const statusTagType = (status?: string | null): string => {
  const map: Record<string, string> = {
    completed: 'success',
    failed: 'danger',
    ignored: 'info',
    identified: '',
    discovered: 'warning',
  }
  return map[status || ''] || ''
}

const mediaTypeLabel = (type?: string | null): string => {
  const map: Record<string, string> = {
    movie: '电影',
    tv: '剧集',
    anime: '动画',
    music: '音乐',
    book: '电子书',
    adult: '成人',
    unknown: '未知',
  }
  return map[type || ''] || type || '-'
}

watch(() => props.episode, loadMetadata, { immediate: true })
</script>

<style scoped lang="scss">
.episode-detail {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
}

/* Hero */
.hero {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

/* 缩略图 */
.thumb-wrapper {
  flex-shrink: 0;
  width: 200px;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-fill-color-darker);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.thumb-image {
  width: 100%;
  height: 100%;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color-dark);

  .ep-num-large {
    font-family: monospace;
    font-size: 22px;
    font-weight: 700;
    color: var(--el-text-color-placeholder);
  }
}

/* Hero 右侧信息 */
.hero-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ep-badge-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;

  .ep-badge {
    font-family: monospace;
    font-weight: 700;
    font-size: 12px;
    color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    border: 1px solid var(--el-color-primary-light-5);
    border-radius: 4px;
    padding: 1px 7px;
    line-height: 20px;
  }
}

.ep-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
  line-height: 1.4;
  word-break: break-word;
}

.ep-subtitle {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0;
  line-height: 1.4;
  word-break: break-word;
}

.ep-meta-row {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 13px;
  color: var(--el-text-color-secondary);

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .rating-inline {
    color: #f59e0b;
    font-weight: 600;
    font-size: 14px;
  }
}

.ep-plot {
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;

  &--empty {
    color: var(--el-text-color-placeholder);
    font-style: italic;
  }
}

/* 操作栏 */
.action-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;

  .action-hint {
    font-size: 12px;
    color: var(--el-text-color-placeholder);
    margin-left: 4px;
  }
}

/* 信息区块 */
.info-section {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;

  .info-section-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    margin-bottom: 12px;
  }
}

/* 路径列表 */
.path-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.path-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;

  .path-label {
    flex-shrink: 0;
    width: 70px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 20px;
    text-align: right;
  }

  .path-value {
    flex: 1;
    min-width: 0;
    font-size: 12px;
    line-height: 20px;
    color: var(--el-text-color-regular);
    word-break: break-all;
  }

  .path-value-row {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: flex-start;
    gap: 6px;

    .path-value {
      flex: 1;
    }
  }

  .path-missing {
    color: var(--el-text-color-placeholder);
    font-style: italic;
  }
}

.mono {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.nfo-plot-text {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
}
</style>
