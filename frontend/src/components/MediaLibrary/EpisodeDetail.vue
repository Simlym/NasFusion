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
            <el-tag size="small" :type="metadata?.has_nfo ? 'success' : 'danger'" effect="plain">
              NFO
            </el-tag>
            <el-tag size="small" :type="metadata?.has_poster ? 'success' : 'warning'" effect="plain">
              图片
            </el-tag>
            <el-tag v-if="fileData.has_subtitle" size="small" type="success" effect="plain">
              字幕
            </el-tag>
          </div>

          <!-- 集标题 -->
          <h2 class="ep-title">
            {{ nfoTitle || fileData.episode_title || fileData.file_name }}
          </h2>

          <!-- 播出日期 + 评分 -->
          <div class="ep-meta-row" v-if="nfoAired || nfoRating">
            <span v-if="nfoAired" class="meta-item">
              <el-icon><Calendar /></el-icon> {{ nfoAired }}
            </span>
            <span v-if="nfoRating" class="rating-inline">
              ★ {{ Number(nfoRating).toFixed(1) }}
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

      <!-- 文件信息（折叠） -->
      <el-collapse class="file-collapse">
        <el-collapse-item title="文件信息" name="file">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="文件名" :span="2">
              <span class="mono">{{ fileData.file_name }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatFileSize(fileData.file_size) }}</el-descriptions-item>
            <el-descriptions-item label="分辨率">{{ fileData.resolution || '-' }}</el-descriptions-item>
            <el-descriptions-item label="集数">
              {{ fileData.episode_number != null ? `第 ${fileData.episode_number} 集` : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="集标题">{{ fileData.episode_title || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>

    </template>

    <el-empty v-else description="请从左侧选择一集" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Document, Calendar } from '@element-plus/icons-vue'
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

/* 文件信息折叠 */
.file-collapse {
  border: none;

  :deep(.el-collapse-item__header) {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    background: transparent;
    border: none;
    padding: 0;
    height: 32px;
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding-bottom: 0;
  }
}

.mono {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
