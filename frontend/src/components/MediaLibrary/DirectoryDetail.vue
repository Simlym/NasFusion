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
              <el-rate
                v-if="detail.nfo_data?.rating"
                :model-value="detail.nfo_data.rating / 2"
                disabled
                show-score
                text-color="#ff9900"
                score-template="{value}"
              />
              <span v-if="detail.nfo_data?.runtime" class="meta-item">{{ detail.nfo_data.runtime }} 分钟</span>
              <span v-if="detail.directory.season_number" class="meta-item">第 {{ detail.directory.season_number }} 季</span>
              <el-tag v-if="detail.directory.media_type" size="small" type="info" effect="dark" class="meta-tag">
                {{ detail.directory.media_type.toUpperCase() }}
              </el-tag>
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
import { ElMessage } from 'element-plus'
import {
  Picture,
  VideoPlay
} from '@element-plus/icons-vue'
import { getDirectoryDetail, type DirectoryDetailResponse } from '@/api/mediaDirectory'
import { getProxiedImageUrl } from '@/utils'

interface Props {
  directoryId: number | null
}

const props = defineProps<Props>()
const loading = ref(false)
const detail = ref<DirectoryDetailResponse | null>(null)
const activeTab = ref('cast')

const defaultPoster = 'https://via.placeholder.com/300x450?text=No+Poster'

// Hero 背景样式（使用 CSS 变量传递给伪元素）
const heroStyle = computed(() => {
  if (detail.value?.directory.backdrop_path) {
    // 使用图片代理，并在 url() 中加引号处理空格和特殊字符
    const proxiedUrl = getProxiedImageUrl(detail.value.directory.backdrop_path)
    return {
      '--backdrop-url': `url("${proxiedUrl}")`
    }
  }
  return {
    backgroundColor: 'var(--nf-bg-container, #221e30)' // 默认深色背景
  }
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

      // 调试日志
      console.log('=== DirectoryDetail Debug ===')
      console.log('has_backdrop:', detail.value.directory.has_backdrop)
      console.log('backdrop_path:', detail.value.directory.backdrop_path)
      console.log('poster_path:', detail.value.directory.poster_path)
      console.log('heroStyle:', heroStyle.value)

      // 根据是否有数据智能切换 Tab
      if (!detail.value.nfo_data?.actors?.length) {
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

// 在 Jellyfin 中打开
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

const formatTime = (timeStr: string) => {
    return new Date(timeStr).toLocaleString()
}

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
  height: 400px;
  color: #fff; /* 强制白色文字 */
  overflow: hidden;
}

/* 背景图片层（带模糊效果） */
.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: cover;
  background-position: center top;
  background-repeat: no-repeat;
  background-image: var(--backdrop-url, none); /* 使用 CSS 变量 */
  filter: blur(8px);
  transform: scale(1.1); /* 放大以避免模糊边缘 */
  z-index: 0;
}

.hero-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  /* 渐变遮罩：上部深色半透明 -> 底部完全不透明背景色，实现融合效果 */
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
  align-items: flex-end; /* 内容底部对齐 */
}

/* Poster */
.poster-wrapper {
  flex-shrink: 0;
  width: 200px;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border: 4px solid rgba(255,255,255,0.1);
  background: #222;
  /* 让海报下沉一点，突出层次感 (可选，这里先对齐) */
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

/* Info */
.info-wrapper {
  flex: 1;
  padding-bottom: 20px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.8);
}

.title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 10px 0;
  line-height: 1.2;

  .year {
    font-weight: 400;
    font-size: 24px;
    opacity: 0.8;
    margin-left: 10px;
  }
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.meta-item {
    font-size: 14px;
    opacity: 0.9;
}

.actions-row {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
}

.genres-row {
    margin-bottom: 15px;
    .genre-tag {
        margin-right: 8px;
        background-color: rgba(255,255,255,0.2) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        color: #fff !important;
    }
}

.plot {
    font-size: 15px;
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
