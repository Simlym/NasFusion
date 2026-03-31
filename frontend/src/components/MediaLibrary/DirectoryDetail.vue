<template>
  <div v-loading="loading" class="detail-container">
    <template v-if="detail">
      <!-- 顶部 Hero 区域 -->
      <div class="hero-section" :style="heroStyle">
        <div class="hero-overlay"></div>
        <div class="hero-content">
          <!-- 左侧海报 -->
          <div class="poster-wrapper">
            <el-image
              :src="getProxiedImageUrl(detail.directory.poster_path) || defaultPoster"
              fit="cover"
              class="poster-image"
              :preview-src-list="detail.directory.poster_path ? [getProxiedImageUrl(detail.directory.poster_path)] : []"
            >
              <template #error>
                <div class="poster-placeholder">
                  <el-icon :size="48"><Picture /></el-icon>
                </div>
              </template>
            </el-image>
          </div>

          <!-- 右侧信息 -->
          <div class="info-wrapper">
            <h1 class="title">
              {{ detail.nfo_data?.title || detail.directory.directory_name }}
              <span v-if="detail.nfo_data?.year" class="year">({{ detail.nfo_data.year }})</span>
            </h1>

            <div class="meta-row">
              <!-- 评分：直接显示原始分值 -->
              <div v-if="detail.nfo_data?.rating" class="rating-badge">
                <span class="star-icon">★</span>
                <span class="rating-num">{{ Number(detail.nfo_data.rating).toFixed(1) }}</span>
                <span class="rating-max">/10</span>
              </div>

              <!-- 外部ID链接 -->
              <a
                v-if="detail.nfo_data?.imdb_id"
                :href="`https://www.imdb.com/title/${detail.nfo_data.imdb_id}`"
                target="_blank"
                class="ext-link"
                @click.stop
              >
                <el-tag size="small" type="warning" effect="dark" class="id-tag">
                  IMDb
                </el-tag>
              </a>
              <a
                v-if="detail.nfo_data?.tmdb_id"
                :href="`https://www.themoviedb.org/${detail.directory.media_type === 'tv' ? 'tv' : 'movie'}/${detail.nfo_data.tmdb_id}`"
                target="_blank"
                class="ext-link"
                @click.stop
              >
                <el-tag size="small" type="primary" effect="dark" class="id-tag">
                  TMDB
                </el-tag>
              </a>

              <span v-if="detail.nfo_data?.runtime" class="meta-item">{{ detail.nfo_data.runtime }} 分钟</span>
              <span v-if="detail.directory.season_number" class="meta-item">第 {{ detail.directory.season_number }} 季</span>
              <el-tag v-if="detail.directory.media_type" size="small" type="info" effect="dark" class="meta-tag">
                {{ detail.directory.media_type.toUpperCase() }}
              </el-tag>
            </div>

            <!-- 元数据状态 -->
            <div class="metadata-status">
              <el-tooltip content="NFO 文件" placement="top">
                <el-tag :type="detail.directory.has_nfo ? 'success' : 'danger'" size="small" effect="dark" class="status-tag">
                  NFO
                </el-tag>
              </el-tooltip>
              <el-tooltip content="海报图片" placement="top">
                <el-tag :type="detail.directory.has_poster ? 'success' : 'danger'" size="small" effect="dark" class="status-tag">
                  海报
                </el-tag>
              </el-tooltip>
              <el-tooltip content="背景图片" placement="top">
                <el-tag :type="detail.directory.has_backdrop ? 'success' : 'info'" size="small" effect="dark" class="status-tag">
                  背景
                </el-tag>
              </el-tooltip>

              <!-- 重新刮削当前目录 -->
              <el-dropdown v-if="videoFiles.length > 0" @command="handleDirectoryAction" style="margin-left: 12px">
                <el-button size="small" type="primary" plain>
                  刮削操作 <el-icon style="margin-left:4px"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="scrape-all">重新刮削全部（图片+NFO）</el-dropdown-item>
                    <el-dropdown-item command="generate-nfo-all">重新生成全部NFO</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div v-if="detail.nfo_data?.genres?.length" class="genres-row">
              <el-tag
                v-for="genre in detail.nfo_data.genres"
                :key="genre"
                size="small"
                effect="plain"
                round
                class="genre-tag"
              >
                {{ genre }}
              </el-tag>
            </div>

            <p class="plot">
              {{ detail.nfo_data?.plot || '暂无简介' }}
            </p>
          </div>
        </div>
      </div>

      <!-- 内容 Tabs 区域 -->
      <div class="content-section">
        <el-tabs v-model="activeTab" class="detail-tabs">

          <!-- 剧集 Tab（仅季度目录显示） -->
          <el-tab-pane v-if="isSeasonDirectory" name="episodes">
            <template #label>
              <span>
                剧集
                <el-badge
                  v-if="missingNfoCount > 0"
                  :value="missingNfoCount"
                  type="danger"
                  style="margin-left: 4px"
                />
              </span>
            </template>

            <div class="episodes-toolbar">
              <div class="episodes-summary">
                <span>{{ videoFiles.length }} 集</span>
                <span class="sep">·</span>
                <el-text :type="missingNfoCount > 0 ? 'danger' : 'success'" size="small">
                  NFO: {{ videoFiles.length - missingNfoCount }}/{{ videoFiles.length }}
                </el-text>
                <span class="sep">·</span>
                <el-text :type="missingPosterCount > 0 ? 'warning' : 'success'" size="small">
                  图片: {{ videoFiles.length - missingPosterCount }}/{{ videoFiles.length }}
                </el-text>
              </div>
              <div class="episodes-actions">
                <el-button
                  size="small"
                  type="primary"
                  :loading="batchScraping"
                  @click="handleBatchScrapeEpisodes"
                >
                  批量刮削（图片+NFO）
                </el-button>
                <el-button
                  size="small"
                  :loading="batchGenerating"
                  @click="handleBatchGenerateNFO"
                >
                  批量生成NFO
                </el-button>
              </div>
            </div>

            <el-table :data="sortedEpisodeFiles" stripe style="width: 100%">
              <el-table-column label="集数" width="70" align="center">
                <template #default="{ row }">
                  <span class="ep-num">
                    {{ row.episode_number != null ? `E${String(row.episode_number).padStart(2, '0')}` : '-' }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="文件名" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                  <div>
                    <div class="ep-title" v-if="row.episode_title">{{ row.episode_title }}</div>
                    <el-text size="small" type="info" class="ep-filename">{{ row.file_name }}</el-text>
                  </div>
                </template>
              </el-table-column>

              <el-table-column prop="resolution" label="分辨率" width="90" align="center" />

              <el-table-column label="NFO" width="60" align="center">
                <template #default="{ row }">
                  <el-icon :color="row.has_nfo ? '#67c23a' : '#f56c6c'" :size="18">
                    <CircleCheck v-if="row.has_nfo" />
                    <CircleClose v-else />
                  </el-icon>
                </template>
              </el-table-column>

              <el-table-column label="图片" width="60" align="center">
                <template #default="{ row }">
                  <el-icon :color="row.has_poster ? '#67c23a' : '#f56c6c'" :size="18">
                    <CircleCheck v-if="row.has_poster" />
                    <CircleClose v-else />
                  </el-icon>
                </template>
              </el-table-column>

              <el-table-column label="字幕" width="60" align="center">
                <template #default="{ row }">
                  <el-icon :color="row.has_subtitle ? '#67c23a' : '#909399'" :size="18">
                    <CircleCheck v-if="row.has_subtitle" />
                    <Minus v-else />
                  </el-icon>
                </template>
              </el-table-column>

              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :loading="scrapingIds.has(row.id)"
                    @click="handleScrapeFile(row.id)"
                  >
                    刮削
                  </el-button>
                  <el-button
                    link
                    type="info"
                    size="small"
                    :loading="generatingIds.has(row.id)"
                    @click="handleGenerateNFOFile(row.id)"
                  >
                    NFO
                  </el-button>
                  <el-button
                    v-if="row.jellyfin_web_url"
                    link
                    type="success"
                    size="small"
                    @click="openInJellyfin(row)"
                  >
                    播放
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 演职人员 Tab -->
          <el-tab-pane label="演职人员" name="cast">
            <div v-if="detail.nfo_data?.actors?.length" class="actors-grid">
              <div v-for="actor in detail.nfo_data.actors" :key="actor.name" class="actor-card">
                <el-avatar :src="getProxiedImageUrl(actor.thumb)" :size="80" shape="circle" class="actor-avatar">
                   {{ actor.name[0] }}
                </el-avatar>
                <div class="actor-info">
                  <div class="actor-name" :title="actor.name">{{ actor.name }}</div>
                  <div class="actor-role" :title="actor.role">{{ actor.role }}</div>
                </div>
              </div>
            </div>
             <el-empty v-else description="暂无演职人员信息" />
          </el-tab-pane>

          <!-- 文件列表 Tab -->
          <el-tab-pane label="文件列表" name="files">
             <div class="files-header">
                <span>共 {{ detail.files.length }} 个文件</span>
                <span class="total-size">总大小: {{ formatFileSize(detail.statistics.total_size) }}</span>
             </div>
             <el-table :data="detail.files" stripe style="width: 100%">
              <el-table-column prop="file_name" label="文件名" min-width="300" show-overflow-tooltip />
               <el-table-column prop="file_size" label="大小" width="100">
                <template #default="{ row }">
                  {{ formatFileSize(row.file_size) }}
                </template>
              </el-table-column>
               <el-table-column prop="resolution" label="分辨率" width="100" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" size="small">
                    {{ getStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.jellyfin_web_url"
                    link
                    type="success"
                    size="small"
                    @click="openInJellyfin(row)"
                    title="在 Jellyfin 中播放"
                  >
                    <el-icon class="el-icon--left"><VideoPlay /></el-icon>
                    Jellyfin
                  </el-button>
                  <el-button link type="primary" size="small">播放</el-button>
                  <el-button link type="primary" size="small">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 技术信息 Tab -->
          <el-tab-pane label="详细信息" name="tech">
            <el-descriptions :column="2" border>
               <el-descriptions-item label="路径" :span="2">{{ detail.directory.directory_path }}</el-descriptions-item>
               <el-descriptions-item label="文件总数">{{ detail.statistics.total_files }}</el-descriptions-item>
               <el-descriptions-item label="视频文件">{{ detail.statistics.video_files }}</el-descriptions-item>
               <el-descriptions-item label="创建时间">{{ formatTime(detail.directory.created_at) }}</el-descriptions-item>
               <el-descriptions-item label="更新时间">{{ formatTime(detail.directory.updated_at) }}</el-descriptions-item>
               <el-descriptions-item label="原始标题">{{ detail.nfo_data?.original_title || '-' }}</el-descriptions-item>
               <el-descriptions-item label="制作公司">{{ detail.nfo_data?.studio || '-' }}</el-descriptions-item>
               <el-descriptions-item label="IMDB ID">
                 <a v-if="detail.nfo_data?.imdb_id" :href="`https://www.imdb.com/title/${detail.nfo_data.imdb_id}`" target="_blank">
                   {{ detail.nfo_data.imdb_id }}
                 </a>
                 <span v-else>-</span>
               </el-descriptions-item>
               <el-descriptions-item label="TMDB ID">{{ detail.nfo_data?.tmdb_id || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
        </el-tabs>
      </div>

    </template>
    <el-empty v-else description="请选择一个目录查看详情" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Picture,
  VideoPlay,
  CircleCheck,
  CircleClose,
  Minus,
  ArrowDown
} from '@element-plus/icons-vue'
import { getDirectoryDetail, type DirectoryDetailResponse } from '@/api/mediaDirectory'
import { scrapeMediaFile, generateNFO, batchScrapeMediaFiles } from '@/api/modules/media'
import { getProxiedImageUrl } from '@/utils'

interface Props {
  directoryId: number | null
}

const props = defineProps<Props>()
const loading = ref(false)
const detail = ref<DirectoryDetailResponse | null>(null)
const activeTab = ref('cast')

// 刮削状态
const scrapingIds = ref<Set<number>>(new Set())
const generatingIds = ref<Set<number>>(new Set())
const batchScraping = ref(false)
const batchGenerating = ref(false)

const defaultPoster = 'https://via.placeholder.com/300x450?text=No+Poster'

// 是否是季度目录（用于显示剧集Tab）
const isSeasonDirectory = computed(() =>
  detail.value?.directory.season_number != null
)

// 视频文件列表（排除字幕、图片等）
const videoFiles = computed(() => {
  if (!detail.value) return []
  return detail.value.files.filter((f: any) =>
    ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'ts', 'flv', 'm2ts', 'rmvb'].includes(
      (f.extension || f.file_name?.split('.').pop() || '').toLowerCase()
    )
  )
})

// 按集数排序的剧集文件
const sortedEpisodeFiles = computed(() => {
  return [...videoFiles.value].sort((a: any, b: any) => {
    const ea = a.episode_number ?? 9999
    const eb = b.episode_number ?? 9999
    return ea - eb
  })
})

// 缺少NFO的集数
const missingNfoCount = computed(() =>
  videoFiles.value.filter((f: any) => !f.has_nfo).length
)

// 缺少图片的集数
const missingPosterCount = computed(() =>
  videoFiles.value.filter((f: any) => !f.has_poster).length
)

// Hero 背景样式
const heroStyle = computed(() => {
  if (detail.value?.directory.backdrop_path) {
    const proxiedUrl = getProxiedImageUrl(detail.value.directory.backdrop_path)
    return { '--backdrop-url': `url("${proxiedUrl}")` }
  }
  return { backgroundColor: 'var(--nf-bg-container, #221e30)' }
})

const loadDetail = async () => {
  if (!props.directoryId) {
    detail.value = null
    return
  }
  loading.value = true
  try {
    const res = await getDirectoryDetail(props.directoryId)
    if (res.data) {
      detail.value = res.data

      // 根据数据智能切换 Tab
      if (res.data.directory.season_number != null) {
        activeTab.value = 'episodes'
      } else if (!res.data.nfo_data?.actors?.length) {
        activeTab.value = 'files'
      } else {
        activeTab.value = 'cast'
      }
    }
  } catch (error) {
    ElMessage.error('加载目录详情失败')
  } finally {
    loading.value = false
  }
}

const refresh = () => loadDetail()

// ===== 刮削操作 =====

async function handleScrapeFile(fileId: number) {
  scrapingIds.value.add(fileId)
  try {
    const res = await scrapeMediaFile(fileId, undefined, true)
    if (res.data.success) {
      ElMessage.success('刮削成功')
      await loadDetail()
    } else {
      ElMessage.error(res.data.error || '刮削失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '刮削失败')
  } finally {
    scrapingIds.value.delete(fileId)
  }
}

async function handleGenerateNFOFile(fileId: number) {
  generatingIds.value.add(fileId)
  try {
    const res = await generateNFO(fileId, undefined, true)
    if (res.data.success) {
      ElMessage.success(`NFO 生成成功`)
      await loadDetail()
    } else {
      ElMessage.error(res.data.error || 'NFO 生成失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'NFO 生成失败')
  } finally {
    generatingIds.value.delete(fileId)
  }
}

async function handleBatchScrapeEpisodes() {
  if (!videoFiles.value.length) return
  const ids = videoFiles.value.map((f: any) => f.id)
  try {
    await ElMessageBox.confirm(
      `确定要刮削全部 ${ids.length} 集文件吗？将覆盖已有的图片和NFO`,
      '批量刮削',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  batchScraping.value = true
  try {
    const res = await batchScrapeMediaFiles({ file_ids: ids })
    ElMessage.success(`批量刮削完成：成功 ${res.data.success_count}，失败 ${res.data.failed_count}`)
    await loadDetail()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '批量刮削失败')
  } finally {
    batchScraping.value = false
  }
}

async function handleBatchGenerateNFO() {
  if (!videoFiles.value.length) return
  const ids = videoFiles.value.map((f: any) => f.id)
  batchGenerating.value = true
  const results = { success: 0, failed: 0 }
  try {
    for (const id of ids) {
      try {
        const res = await generateNFO(id, undefined, true)
        if (res.data.success) results.success++
        else results.failed++
      } catch {
        results.failed++
      }
    }
    ElMessage.success(`NFO生成完成：成功 ${results.success}，失败 ${results.failed}`)
    await loadDetail()
  } finally {
    batchGenerating.value = false
  }
}

async function handleDirectoryAction(command: string) {
  if (command === 'scrape-all') {
    await handleBatchScrapeEpisodes()
  } else if (command === 'generate-nfo-all') {
    await handleBatchGenerateNFO()
  }
}

// ===== 工具函数 =====

const openInJellyfin = (file: any) => {
  if (file.jellyfin_web_url) {
    window.open(file.jellyfin_web_url, '_blank')
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

const formatTime = (timeStr: string) => new Date(timeStr).toLocaleString()

const getStatusType = (status: string) => {
  const map: any = { discovered: 'info', identified: 'success', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const map: any = { discovered: '已发现', identified: '已识别', completed: '已完成' }
  return map[status] || status
}

watch(() => props.directoryId, loadDetail, { immediate: true })

defineExpose({ refresh })
</script>

<style scoped lang="scss">
.detail-container {
  height: 100%;
  overflow-y: auto;
  background-color: var(--el-bg-color);
  position: relative;
}

/* Hero Section */
.hero-section {
  position: relative;
  width: 100%;
  height: 420px;
  color: #fff;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-size: cover;
  background-position: center top;
  background-repeat: no-repeat;
  background-image: var(--backdrop-url, none);
  filter: blur(8px);
  transform: scale(1.1);
  z-index: 0;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.6) 0%,
    rgba(0, 0, 0, 0.8) 70%,
    var(--el-bg-color) 100%
  );
  z-index: 1;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px;
  display: flex;
  gap: 40px;
  height: 100%;
  align-items: flex-end;
}

.poster-wrapper {
  flex-shrink: 0;
  width: 200px;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border: 4px solid rgba(255,255,255,0.1);
  background: #222;
}

.poster-image {
  width: 100%;
  height: 100%;
}

.poster-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: #333;
  color: #666;
}

.info-wrapper {
  flex: 1;
  padding-bottom: 20px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.8);
}

.title {
  font-size: 30px;
  font-weight: 700;
  margin: 0 0 10px 0;
  line-height: 1.2;

  .year {
    font-weight: 400;
    font-size: 22px;
    opacity: 0.8;
    margin-left: 10px;
  }
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

/* 评分徽章 */
.rating-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  background: rgba(255, 153, 0, 0.2);
  border: 1px solid rgba(255, 153, 0, 0.5);
  border-radius: 6px;
  padding: 2px 10px;

  .star-icon {
    font-size: 14px;
    color: #ff9900;
  }

  .rating-num {
    font-size: 20px;
    font-weight: 700;
    color: #ff9900;
    line-height: 1;
  }

  .rating-max {
    font-size: 12px;
    color: rgba(255, 153, 0, 0.7);
  }
}

.ext-link {
  text-decoration: none;
  .id-tag {
    cursor: pointer;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.meta-item {
  font-size: 14px;
  opacity: 0.9;
}

.meta-tag {
  backdrop-filter: blur(4px);
}

/* 元数据状态行 */
.metadata-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .status-tag {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.genres-row {
  margin-bottom: 12px;

  .genre-tag {
    margin-right: 8px;
    background-color: rgba(255,255,255,0.2) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #fff !important;
  }
}

.plot {
  font-size: 14px;
  line-height: 1.6;
  opacity: 0.9;
  max-width: 800px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Content Section */
.content-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 40px;
}

/* 剧集 Tab */
.episodes-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;

  .episodes-summary {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--el-text-color-primary);
    font-weight: 500;

    .sep {
      color: var(--el-text-color-placeholder);
    }
  }

  .episodes-actions {
    display: flex;
    gap: 8px;
  }
}

.ep-num {
  font-family: monospace;
  font-weight: 600;
  font-size: 13px;
  color: var(--el-color-primary);
}

.ep-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  line-height: 1.4;
}

.ep-filename {
  font-size: 11px;
  display: block;
  margin-top: 2px;
}

/* 演职人员 */
.actors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 20px;
  padding-top: 10px;
}

.actor-card {
  text-align: center;

  .actor-avatar {
    margin-bottom: 10px;
    border: 2px solid var(--el-border-color-lighter);
  }

  .actor-name {
    font-weight: 500;
    font-size: 14px;
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .actor-role {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

/* 文件列表 */
.files-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

:deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
}
</style>
