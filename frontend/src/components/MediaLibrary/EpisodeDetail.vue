<template>
  <div v-loading="loading" class="episode-detail">
    <template v-if="fileData">
      <!-- 头部信息 -->
      <div class="episode-header">
        <div class="episode-title-row">
          <span class="ep-num-badge" v-if="fileData.episode_number != null">
            E{{ String(fileData.episode_number).padStart(2, '0') }}
          </span>
          <h2 class="ep-title">{{ fileData.episode_title || fileData.file_name }}</h2>
        </div>
        <p class="ep-filename">{{ fileData.file_name }}</p>
        <div class="ep-meta">
          <span v-if="fileData.resolution" class="meta-chip">{{ fileData.resolution }}</span>
          <span v-if="fileData.file_size" class="meta-chip">{{ formatFileSize(fileData.file_size) }}</span>
        </div>
      </div>

      <!-- 刮削状态卡片 -->
      <div class="scrape-status-card">
        <div class="status-title">刮削状态</div>
        <div class="status-grid">
          <!-- NFO -->
          <div class="status-item" :class="fileData.has_nfo ? 'status-ok' : 'status-missing'">
            <el-icon :size="28">
              <CircleCheck v-if="fileData.has_nfo" />
              <CircleClose v-else />
            </el-icon>
            <span class="status-label">NFO 文件</span>
            <span class="status-desc">{{ fileData.has_nfo ? '已存在' : '缺少' }}</span>
          </div>

          <!-- 图片 -->
          <div class="status-item" :class="fileData.has_poster ? 'status-ok' : 'status-warn'">
            <el-icon :size="28">
              <CircleCheck v-if="fileData.has_poster" />
              <CircleClose v-else />
            </el-icon>
            <span class="status-label">缩略图</span>
            <span class="status-desc">{{ fileData.has_poster ? '已存在' : '缺少' }}</span>
          </div>

          <!-- 字幕 -->
          <div class="status-item" :class="fileData.has_subtitle ? 'status-ok' : 'status-neutral'">
            <el-icon :size="28">
              <CircleCheck v-if="fileData.has_subtitle" />
              <Minus v-else />
            </el-icon>
            <span class="status-label">字幕文件</span>
            <span class="status-desc">{{ fileData.has_subtitle ? '已存在' : '无' }}</span>
          </div>
        </div>
      </div>

      <!-- 操作区 -->
      <div class="action-section">
        <div class="action-title">刮削操作</div>
        <div class="action-buttons">
          <el-button
            type="primary"
            :loading="scraping"
            :icon="Download"
            @click="handleScrape"
          >
            重新刮削（图片 + NFO）
          </el-button>
          <el-button
            :loading="generating"
            :icon="Document"
            @click="handleGenerateNFO"
          >
            仅生成 NFO
          </el-button>
        </div>
        <el-text type="info" size="small" style="margin-top: 8px; display: block">
          刮削将强制覆盖已有的缩略图和 NFO 文件
        </el-text>
      </div>

      <!-- 文件详情 -->
      <div class="file-info-section">
        <div class="action-title">文件信息</div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="文件名">{{ fileData.file_name }}</el-descriptions-item>
          <el-descriptions-item label="分辨率">{{ fileData.resolution || '-' }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(fileData.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="集数">
            {{ fileData.episode_number != null ? `第 ${fileData.episode_number} 集` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="fileData.episode_title" label="集标题">
            {{ fileData.episode_title }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </template>

    <el-empty v-else description="请从左侧选择一集" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, CircleClose, Minus, Download, Document } from '@element-plus/icons-vue'
import { scrapeMediaFile, generateNFO } from '@/api/modules/media'
import { getMediaFile } from '@/api/mediaFile'
import type { EpisodeTreeNode } from './DirectoryTree.vue'

interface Props {
  episode: EpisodeTreeNode | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'scrape-done'): void
}>()

const loading = ref(false)
const scraping = ref(false)
const generating = ref(false)

// 使用本地副本，以便刮削后刷新状态
const fileData = ref<EpisodeTreeNode | null>(null)

/** 从树节点初始化，再从API刷新状态 */
const loadFileStatus = async () => {
  if (!props.episode) {
    fileData.value = null
    return
  }
  // 先用树节点数据快速显示
  fileData.value = { ...props.episode }

  // 再异步刷新，获取最新状态
  loading.value = true
  try {
    const res = await getMediaFile(props.episode.id)
    if (res.data) {
      fileData.value = {
        ...props.episode,
        has_nfo: res.data.has_nfo,
        has_poster: res.data.has_poster,
        has_subtitle: res.data.has_subtitle,
        resolution: res.data.resolution ?? props.episode.resolution,
        file_size: res.data.file_size ?? props.episode.file_size,
        episode_number: res.data.episode_number ?? props.episode.episode_number,
        episode_title: res.data.episode_title ?? props.episode.episode_title,
        file_name: res.data.file_name,
      }
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
      await loadFileStatus()
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
      await loadFileStatus()
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

watch(() => props.episode, loadFileStatus, { immediate: true })
</script>

<style scoped lang="scss">
.episode-detail {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.episode-header {
  .episode-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
  }

  .ep-num-badge {
    flex-shrink: 0;
    font-family: monospace;
    font-weight: 700;
    font-size: 16px;
    color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    border-radius: 6px;
    padding: 2px 10px;
    border: 1px solid var(--el-color-primary-light-5);
  }

  .ep-title {
    font-size: 22px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin: 0;
    line-height: 1.3;
  }

  .ep-filename {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    margin: 0 0 10px;
    word-break: break-all;
  }

  .ep-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .meta-chip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    background: var(--el-fill-color);
    border-radius: 4px;
    padding: 2px 8px;
    border: 1px solid var(--el-border-color-light);
  }
}

.scrape-status-card {
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 16px;

  .status-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 14px;
  }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 14px 8px;
    border-radius: 8px;
    border: 1px solid transparent;

    &.status-ok {
      background: var(--el-color-success-light-9);
      border-color: var(--el-color-success-light-5);
      .el-icon { color: var(--el-color-success); }
    }

    &.status-missing {
      background: var(--el-color-danger-light-9);
      border-color: var(--el-color-danger-light-5);
      .el-icon { color: var(--el-color-danger); }
    }

    &.status-warn {
      background: var(--el-color-warning-light-9);
      border-color: var(--el-color-warning-light-5);
      .el-icon { color: var(--el-color-warning); }
    }

    &.status-neutral {
      background: var(--el-fill-color-light);
      border-color: var(--el-border-color-light);
      .el-icon { color: var(--el-text-color-placeholder); }
    }

    .status-label {
      font-size: 13px;
      font-weight: 500;
      color: var(--el-text-color-primary);
    }

    .status-desc {
      font-size: 11px;
      color: var(--el-text-color-secondary);
    }
  }
}

.action-section {
  .action-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }

  .action-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
}

.file-info-section {
  .action-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }
}
</style>
