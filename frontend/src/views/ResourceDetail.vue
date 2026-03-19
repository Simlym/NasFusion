<template>
  <div v-loading="loading" class="resource-detail-container">
    <div v-if="resource">
      <!-- 顶部操作栏 -->
      <div class="page-header">
        <el-page-header @back="goBack">
          <template #content>
            <span class="resource-title">{{ resource.title }}</span>
          </template>
          <template #extra>
            <div class="header-actions">
              <el-button
                type="primary"
                :icon="View"
                @click="openOriginalSite"
              >
                原站点页面
              </el-button>
              <el-button
                type="success"
                :icon="Download"
                @click="handleDownload"
              >
                下载
              </el-button>
            </div>
          </template>
        </el-page-header>
      </div>

      <!-- 基础信息卡片 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>基础信息</span>
            <el-tag v-if="resource.identificationStatus === 'identified'" type="success" size="small">
              已识别
            </el-tag>
            <el-tag v-else-if="resource.identificationStatus === 'failed'" type="danger" size="small">
              识别失败
            </el-tag>
            <el-tag v-else type="info" size="small" effect="plain">
              未识别
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="descCols" border>
          <el-descriptions-item label="站点名称">
            {{ resource.siteName || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="分类">
            <el-tag :type="getCategoryType(resource.category)" size="small">
              {{ getCategoryLabel(resource.category) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="标题">
            {{ resource.title }}
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.subtitle" label="副标题">
            {{ resource.subtitle }}
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ resource.sizeHumanReadable }} ({{ resource.sizeGb }} GB)
          </el-descriptions-item>
          <el-descriptions-item label="文件数量">
            {{ resource.fileCount }} 个
          </el-descriptions-item>
          <el-descriptions-item label="发布时间">
            {{ formatPublishedTime(resource.publishedAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="种子ID">
            {{ resource.torrentId }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 做种信息 -->
      <el-card class="info-card">
        <template #header>
          <span>做种信息</span>
        </template>

        <el-descriptions :column="descCols3" border>
          <el-descriptions-item label="做种数">
            <el-statistic :value="resource.seeders" />
          </el-descriptions-item>
          <el-descriptions-item label="下载数">
            <el-statistic :value="resource.leechers" />
          </el-descriptions-item>
          <el-descriptions-item label="完成数">
            <el-statistic :value="resource.completions" />
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 促销信息 -->
      <el-card v-if="resource.isPromotional" class="info-card">
        <template #header>
          <span>促销信息</span>
        </template>

        <el-space wrap>
          <el-tag v-if="resource.isFree" type="success" effect="dark">
            免费
          </el-tag>
          <el-tag v-if="resource.isDiscount" type="warning" effect="dark">
            折扣
          </el-tag>
          <el-tag v-if="resource.isDoubleUpload" type="info" effect="dark">
            双倍上传
          </el-tag>
          <span v-if="resource.promotionExpireAt" class="promotion-expire">
            促销到期: {{ formatPublishedTime(resource.promotionExpireAt) }}
          </span>
        </el-space>
      </el-card>

      <!-- HR要求 -->
      <el-card v-if="resource.hasHr" class="info-card">
        <template #header>
          <span>HR要求</span>
        </template>

        <el-alert type="warning" :closable="false">
          <template #title>
            <div v-if="resource.hrDays || resource.hrSeedTime || resource.hrRatio">
              <div v-if="resource.hrDays">保种天数: {{ resource.hrDays }} 天</div>
              <div v-if="resource.hrSeedTime">保种时长: {{ resource.hrSeedTime }} 小时</div>
              <div v-if="resource.hrRatio">分享率: {{ resource.hrRatio }}</div>
            </div>
            <div v-else>该资源有HR要求，请务必遵守保种规则</div>
          </template>
        </el-alert>
      </el-card>

      <!-- 质量信息 -->
      <el-card v-if="hasQualityInfo" class="info-card">
        <template #header>
          <span>质量信息</span>
        </template>

        <el-descriptions :column="descCols" border>
          <el-descriptions-item v-if="resource.resolution" label="分辨率">
            {{ resource.resolution }}
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.source" label="来源">
            {{ resource.source }}
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.codec" label="编码">
            {{ resource.codec }}
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.audio && resource.audio.length" label="音轨">
            {{ resource.audio.join(', ') }}
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.subtitleInfo && resource.subtitleInfo.length" label="字幕">
            {{ resource.subtitleInfo.join(', ') }}
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.qualityTags && resource.qualityTags.length" label="其他标签">
            <el-space wrap>
              <el-tag v-for="tag in resource.qualityTags" :key="tag" size="small">
                {{ tag }}
              </el-tag>
            </el-space>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 电视剧信息 -->
      <el-card v-if="resource.category === 'tv' && resource.tvInfo" class="info-card">
        <template #header>
          <span>剧集信息</span>
        </template>

        <el-descriptions :column="1" border>
          <el-descriptions-item label="季度">
            <el-tag v-for="season in resource.tvInfo.seasons" :key="season" size="small" style="margin-right: 5px">
              S{{ season }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.tvInfo.episodes" label="集数">
            <div v-for="(epInfo, season) in resource.tvInfo.episodes" :key="season">
              S{{ season }}: 第 {{ epInfo.start }} - {{ epInfo.end }} 集
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="是否完整季">
            <el-tag :type="resource.tvInfo.isCompleteSeason ? 'success' : 'info'" size="small">
              {{ resource.tvInfo.isCompleteSeason ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 评分信息 -->
      <el-card v-if="hasRatingInfo" class="info-card">
        <template #header>
          <span>评分信息</span>
        </template>

        <el-space :size="20">
          <div v-if="resource.imdbId" class="rating-item">
            <div class="rating-label">IMDB</div>
            <div class="rating-value">
              {{ resource.imdbRating || '-' }}
              <span class="rating-link" @click="openIMDB">查看 →</span>
            </div>
          </div>
          <div v-if="resource.doubanId" class="rating-item">
            <div class="rating-label">豆瓣</div>
            <div class="rating-value">
              {{ resource.doubanRating || '-' }}
              <span class="rating-link" @click="openDouban">查看 →</span>
            </div>
          </div>
          <div v-if="resource.tmdbId" class="rating-item">
            <div class="rating-label">TMDB</div>
            <div class="rating-value">
              {{ resource.tmdbId || '-' }}
              <span class="rating-link" @click="openTMDB">查看 →</span>
            </div>
          </div>
        </el-space>
      </el-card>

      <!-- 详细描述 -->
      <el-card v-if="resource.description" class="info-card">
        <template #header>
          <div class="card-header">
            <span>详细描述</span>
            <el-button
              v-if="!resource.detailFetched"
              type="primary"
              size="small"
              :loading="fetchingDetail"
              @click="fetchResourceDetail"
            >
              获取完整详情
            </el-button>
          </div>
        </template>

        <div class="description-content" v-html="formatDescription(resource.description)"></div>
      </el-card>

      <!-- MediaInfo -->
      <el-card v-if="resource.mediainfo" class="info-card">
        <template #header>
          <span>MediaInfo</span>
        </template>

        <pre class="mediainfo-content">{{ resource.mediainfo }}</pre>
      </el-card>

      <!-- 下载链接 -->
      <el-card class="info-card">
        <template #header>
          <span>下载链接</span>
        </template>

        <el-descriptions :column="1" border>
          <el-descriptions-item label="种子下载">
            <el-input
              v-model="resource.downloadUrl"
              readonly
              :suffix-icon="CopyDocument"
              @click:suffix-icon="copyToClipboard(resource.downloadUrl, '种子链接已复制')"
            />
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.magnetLink" label="磁力链接">
            <el-input
              v-model="resource.magnetLink"
              readonly
              :suffix-icon="CopyDocument"
              @click:suffix-icon="copyToClipboard(resource.magnetLink, '磁力链接已复制')"
            />
          </el-descriptions-item>
          <el-descriptions-item v-if="resource.torrentHash" label="种子哈希">
            <el-input
              v-model="resource.torrentHash"
              readonly
              :suffix-icon="CopyDocument"
              @click:suffix-icon="copyToClipboard(resource.torrentHash, '哈希值已复制')"
            />
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>

    <!-- 下载对话框 -->
    <DownloadDialog
      v-model="downloadDialogVisible"
      :resource="resource"
      @success="handleDownloadSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { View, Download, CopyDocument } from '@element-plus/icons-vue'
import api from '@/api'
import type { PTResource } from '@/types'
import DownloadDialog from '@/components/download/DownloadDialog.vue'

const route = useRoute()
const router = useRouter()

// 状态
const loading = ref(false)
const fetchingDetail = ref(false)
const resource = ref<PTResource | null>(null)
const downloadDialogVisible = ref(false)

// 移动端响应式列数
const windowWidth = ref(window.innerWidth)
const handleResize = () => { windowWidth.value = window.innerWidth }
const isMobile = computed(() => windowWidth.value <= 768)
const descCols = computed(() => isMobile.value ? 1 : 2)
const descCols3 = computed(() => isMobile.value ? 1 : 3)

// 计算属性
const hasQualityInfo = computed(() => {
  return resource.value?.resolution || resource.value?.source || resource.value?.codec ||
         (resource.value?.audio && resource.value.audio.length) ||
         (resource.value?.subtitleInfo && resource.value.subtitleInfo.length) ||
         (resource.value?.qualityTags && resource.value.qualityTags.length)
})

const hasRatingInfo = computed(() => {
  return resource.value?.imdbId || resource.value?.doubanId || resource.value?.tmdbId
})

// 加载资源详情
const loadResourceDetail = async () => {
  const resourceId = Number(route.params.id)
  if (!resourceId) {
    ElMessage.error('无效的资源ID')
    router.back()
    return
  }

  loading.value = true
  try {
    const response = await api.resource.getPTResourceDetail(resourceId)
    if (response?.data) {
      resource.value = response.data as any
    }
  } catch (error) {
    console.error('Failed to load resource detail:', error)
    ElMessage.error('加载资源详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

// 获取完整详情
const fetchResourceDetail = async () => {
  if (!resource.value) return

  fetchingDetail.value = true
  try {
    const response = await api.resource.fetchPTResourceDetail(resource.value.id)
    if (response?.data) {
      resource.value = response.data as any
      ElMessage.success('获取详情成功')
    }
  } catch (error: any) {
    console.error('Failed to fetch detail:', error)
    ElMessage.error(error.response?.data?.detail || '获取详情失败')
  } finally {
    fetchingDetail.value = false
  }
}

// 打开原站点页面
const openOriginalSite = () => {
  if (!resource.value?.detailUrl) {
    ElMessage.warning('该资源没有原站点链接')
    return
  }
  window.open(resource.value.detailUrl, '_blank')
}

// 打开IMDB
const openIMDB = () => {
  if (!resource.value?.imdbId) return
  window.open(`https://www.imdb.com/title/${resource.value.imdbId}`, '_blank')
}

// 打开豆瓣
const openDouban = () => {
  if (!resource.value?.doubanId) return
  window.open(`https://movie.douban.com/subject/${resource.value.doubanId}`, '_blank')
}

// 打开TMDB
const openTMDB = () => {
  if (!resource.value?.tmdbId) return
  window.open(`https://www.themoviedb.org/movie/${resource.value.tmdbId}`, '_blank')
}

// 复制到剪贴板
const copyToClipboard = async (text: string, message: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(message)
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 返回
const goBack = () => {
  router.back()
}

// 处理下载
const handleDownload = () => {
  if (resource.value) {
    downloadDialogVisible.value = true
  }
}

// 下载成功回调
const handleDownloadSuccess = () => {
  ElMessage.success('下载任务创建成功')
}

// 格式化发布时间
const formatPublishedTime = (dateString: string | undefined) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化描述（处理BB代码）
const formatDescription = (description: string) => {
  if (!description) return ''
  // 简单的BB代码转换
  return description
    .replace(/\[b\](.*?)\[\/b\]/g, '<strong>$1</strong>')
    .replace(/\[i\](.*?)\[\/i\]/g, '<em>$1</em>')
    .replace(/\[u\](.*?)\[\/u\]/g, '<u>$1</u>')
    .replace(/\[url=(.*?)\](.*?)\[\/url\]/g, '<a href="$1" target="_blank">$2</a>')
    .replace(/\[img\](.*?)\[\/img\]/g, '<img src="$1" style="max-width: 100%;" />')
    .replace(/\n/g, '<br/>')
}

// 获取分类类型
const getCategoryType = (category: string) => {
  const typeMap: Record<string, any> = {
    movie: 'primary',
    tv: 'success',
    music: 'warning',
    anime: 'danger',
    book: 'info',
    game: '',
    adult: 'danger',
    other: 'info'
  }
  return typeMap[category] || 'info'
}

// 获取分类标签
const getCategoryLabel = (category: string) => {
  const labelMap: Record<string, string> = {
    movie: '电影',
    tv: '电视剧',
    music: '音乐',
    anime: '动漫',
    book: '书籍',
    game: '游戏',
    adult: '成人',
    other: '其他'
  }
  return labelMap[category] || category
}

onMounted(() => {
  loadResourceDetail()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.resource-detail-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.resource-title {
  font-size: 18px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-card {
  margin-bottom: 20px;
}

.promotion-expire {
  color: #909399;
  font-size: 14px;
}

.rating-item {
  text-align: center;
}

.rating-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.rating-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.rating-link {
  font-size: 14px;
  color: #409eff;
  cursor: pointer;
  margin-left: 5px;
}

.rating-link:hover {
  text-decoration: underline;
}

.description-content {
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.mediainfo-content {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

:deep(.el-descriptions__label) {
  width: 120px;
  font-weight: 500;
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .resource-detail-container {
    padding: 12px;
  }

  .header-actions {
    flex-wrap: wrap;
    gap: 8px;
  }

  .card-header {
    flex-wrap: wrap;
    gap: 6px;
    align-items: flex-start;
  }

  /* descriptions label 在小屏下缩短 */
  :deep(.el-descriptions__label) {
    width: 80px;
  }
}
</style>
