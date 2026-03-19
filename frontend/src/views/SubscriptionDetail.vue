<template>
  <div class="page-container">
    <el-page-header @back="handleBack">
      <template #content>
        <span class="page-title">订阅详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" class="detail-container">
      <!-- 订阅信息卡片 -->
      <el-card v-if="subscription" class="subscription-info-card">
        <template #header>
          <div class="card-header">
            <span>订阅信息</span>
            <div class="header-actions">
              <el-button
                v-if="subscription.status === 'active'"
                type="warning"
                :icon="VideoPause"
                @click="handlePause"
              >
                暂停
              </el-button>
              <el-button
                v-else-if="subscription.status === 'paused'"
                type="success"
                :icon="VideoPlay"
                @click="handleResume"
              >
                恢复
              </el-button>
              <el-button type="primary" :icon="Edit" @click="handleEdit">编辑</el-button>
            </div>
          </div>
        </template>

        <div class="subscription-detail">
          <div class="detail-row">
            <el-image
              v-if="subscription.posterUrl"
              :src="getProxiedImageUrl(subscription.posterUrl)"
              fit="cover"
              class="poster"
            />
            <div class="info">
              <h2>{{ subscription.title }}</h2>
              <p v-if="subscription.originalTitle" class="original-title">{{ subscription.originalTitle }}</p>

              <div class="meta">
                <el-tag :type="subscription.status === 'active' ? 'success' : 'warning'">
                  {{ getStatusText(subscription.status) }}
                </el-tag>
                <el-tag :type="subscription.mediaType === 'tv' ? 'success' : 'primary'">
                  {{ subscription.mediaType === 'tv' ? '电视剧' : '电影' }}
                </el-tag>
                <span v-if="subscription.year">{{ subscription.year }}</span>
              </div>

              <div v-if="subscription.mediaType === 'tv'" class="season-info">
                <strong>订阅季度：</strong>第 {{ subscription.currentSeason }} 季
                <span v-if="subscription.startEpisode"> · 从第 {{ subscription.startEpisode }} 集开始</span>
                <span v-if="subscription.currentEpisode"> · 已匹配到第 {{ subscription.currentEpisode }} 集</span>
              </div>

              <div class="extra-info">
                <span>创建于：{{ formatDateTime(subscription.createdAt) }}</span>
                <span class="dot">·</span>
                <span>最后检查：{{ subscription.lastCheckAt ? formatDateTime(subscription.lastCheckAt) : '尚未检查' }}</span>
                <span class="dot">·</span>
                <el-tag :type="subscription.autoDownload ? 'success' : 'info'" size="small">
                  自动下载：{{ subscription.autoDownload ? '已开启' : '已关闭' }}
                </el-tag>
                <el-tag v-if="subscription.autoDownload" :type="subscription.autoOrganize ? 'success' : 'warning'" size="small">
                  自动整理：{{ subscription.autoOrganize ? '已开启' : '已关闭' }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 集数状态（仅电视剧订阅） -->
      <el-card v-if="subscription && subscription.mediaType === 'tv'" class="episodes-card">
        <EpisodeStatusGrid
          v-if="episodesStatus"
          :episodes="episodesStatus.episodes"
          :stats="episodesStatus.stats"
          :season="episodesStatus.season"
          :total-episodes="episodesStatus.totalEpisodes"
          :start-episode="episodesStatus.startEpisode"
          :loading="episodesLoading"
          @refresh="handleRefreshEpisodes"
          @view-resources="handleViewResources"
          @search-episode="handleSearchEpisode"
          @mark-status="handleMarkEpisodeStatus"
        />
        <el-empty v-else description="暂无集数状态数据" />
      </el-card>

      <!-- 匹配的PT资源 -->
      <el-card class="matched-resources-card">
        <template #header>
          <div class="card-header">
            <span>匹配的PT资源 ({{ resourceTotal }})</span>
            <div class="header-actions">
              <el-tag 
                v-if="resourceEpisodeFilter" 
                closable 
                type="warning" 
                @close="resourceEpisodeFilter = null"
              >
                筛选: 第 {{ resourceEpisodeFilter }} 集
              </el-tag>
              <el-button type="primary" plain size="small" :icon="Search" @click="handleManualSync">手动同步资源</el-button>
            </div>
          </div>
        </template>
        <div ref="resourcesTableRef" class="resources-table-container">
          <el-table v-loading="resourcesLoading" :data="filteredResources">
          <el-table-column prop="title" label="标题" min-width="300">
            <template #default="{ row }">
              <div>
                <div class="resource-title">
                  {{ row.title }}
                  <el-tag v-if="row.isDownloaded" type="success" size="small" style="margin-left: 8px">
                    已下载
                  </el-tag>
                </div>
                <div v-if="row.subtitle" class="resource-subtitle">{{ row.subtitle }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="siteName" label="站点" width="100" />
          <el-table-column v-if="subscription && subscription.mediaType === 'tv'" label="集数" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.tvInfo" size="small" type="primary">
                {{ formatTvInfo(row.tvInfo, subscription.currentSeason) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="质量" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.resolution" size="small" type="info">
                {{ row.resolution }}
              </el-tag>
              <span v-else style="color: var(--text-color-muted)">-</span>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="100">
            <template #default="{ row }">
              {{ formatSize(row.sizeBytes) }}
            </template>
          </el-table-column>
          <el-table-column prop="seeders" label="做种" width="80" />
          <el-table-column label="促销" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.promotionType === 'free'" type="success" size="small">免费</el-tag>
              <el-tag v-else-if="row.promotionType === '2xfree'" type="success" size="small">2X免费</el-tag>
              <el-tag v-else-if="row.promotionType === '2x'" type="info" size="small">2X上传</el-tag>
              <el-tag v-else-if="row.promotionType === '50%'" type="warning" size="small">50%</el-tag>
              <el-tag v-else-if="row.promotionType === '2x50%'" type="warning" size="small">2X50%</el-tag>
              <span v-else style="color: var(--text-color-muted)">-</span>
            </template>
          </el-table-column>
          <el-table-column label="发布时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.publishedAt) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button link type="success" size="small" @click="handleDownload(row)">
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="matchedResources.length === 0" description="暂无匹配资源" />
        </div>
      </el-card>

    </div>

    <!-- 编辑对话框 -->
    <SubscriptionDialog
      v-model:visible="editDialogVisible"
      :is-edit="true"
      :edit-data="subscription"
      @success="handleEditSuccess"
    />

    <!-- 下载对话框 -->
    <DownloadDialog
      v-model="downloadDialogVisible"
      :resource="currentDownloadResource"
      :unified-table-name="subscription?.mediaType === 'movie' ? 'unified_movies' : 'unified_tv_series'"
      :unified-resource-id="subscription?.mediaType === 'movie' ? subscription?.unifiedMovieId : subscription?.unifiedTvId"
      @success="handleDownloadSuccess"
    />

    <!-- 手动同步对话框 -->
    <el-dialog
      v-model="syncDialogVisible"
      title="手动同步资源"
      width="500px"
      append-to-body
    >
      <div class="sync-dialog-content">
        <p class="dialog-tip" style="margin-bottom: 15px; color: var(--text-color-regular); font-size: 14px;">
          将从所有启用的PT站点搜索并同步资源。您可以修改搜索关键字以提高匹配准确率。
        </p>
        <el-form label-position="top">
          <el-form-item label="搜索关键字">
            <el-input 
              v-model="syncKeyword" 
              placeholder="请输入搜索关键字" 
              @keyup.enter="executeSync"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="syncDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="syncing" @click="executeSync">
            开始同步
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, VideoPause, VideoPlay, Download, Search } from '@element-plus/icons-vue'
import {
  getSubscriptionDetail,
  getEpisodesStatus,
  refreshEpisodesStatus,
  pauseSubscription,
  resumeSubscription,
  syncSubscriptionPTResources,
  updateEpisodeStatus
} from '@/api/modules/subscription'
import { getPTResourceList } from '@/api/modules/resource'
import SubscriptionDialog from '@/components/subscription/SubscriptionDialog.vue'
import EpisodeStatusGrid from '@/components/subscription/EpisodeStatusGrid.vue'
import DownloadDialog from '@/components/download/DownloadDialog.vue'
import type { Subscription } from '@/types/subscription'
import { getProxiedImageUrl } from '@/utils'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const resourcesLoading = ref(false)
const episodesLoading = ref(false)
const subscription = ref<Subscription | null>(null)
const matchedResources = ref<any[]>([])
const resourceTotal = ref(0)
const episodesStatus = ref<any>(null)
const editDialogVisible = ref(false)
const downloadDialogVisible = ref(false)
const currentDownloadResource = ref<any>(null)
const resourceEpisodeFilter = ref<number | null>(null)
const resourcesTableRef = ref<HTMLElement | null>(null)

// Manual Sync Refs
const syncDialogVisible = ref(false)
const syncKeyword = ref('')
const syncing = ref(false)

// 过滤后的资源列表
const filteredResources = computed(() => {
  if (!resourceEpisodeFilter.value) {
    return matchedResources.value
  }
  return matchedResources.value.filter(resource => {
    // 简单的集数匹配逻辑，这取决于 resource.tvInfo 的结构
    // 假设 resource.tvInfo.episodes[season].start/end 包含该集
    if (!subscription.value?.currentSeason || !resource.tvInfo?.episodes) return false
    
    const episodes = resource.tvInfo.episodes[String(subscription.value.currentSeason)]
    if (!episodes) return false
    
    const target = resourceEpisodeFilter.value!
    // 如果是单集
    if (episodes.start === episodes.end) {
      return episodes.start === target
    }
    // 如果是范围
    if (episodes.start <= target && episodes.end >= target) {
      return true
    }
    return false
  })
})

// 处理查看资源
const handleViewResources = (episode: number) => {
  resourceEpisodeFilter.value = episode
  // 滚动到资源列表
  setTimeout(() => {
    resourcesTableRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, 100)
}

// 处理搜索集数
const handleSearchEpisode = (episode: number) => {
  ElMessage.info(`正在开发中：搜索第 ${episode} 集功能`)
  // TODO: 跳转到搜索页面或打开搜索对话框
}

// 加载订阅详情
const loadSubscriptionDetail = async () => {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const res = await getSubscriptionDetail(id)
    subscription.value = res.data
  } catch (error) {
    ElMessage.error('加载订阅详情失败')
  } finally {
    loading.value = false
  }
}

// 加载匹配资源
const loadMatchedResources = async () => {
  resourcesLoading.value = true
  try {
    const id = Number(route.params.id)
    // 使用PT资源API，传入subscriptionId参数
    const res = await getPTResourceList({
      subscriptionId: id,
      page: 1,
      pageSize: 100
    })
    // 按集数降序排序（集数大的在前面）
    const resources = res.data.items || []
    matchedResources.value = resources.sort((a, b) => {
      // 获取当前订阅的季度
      const season = subscription.value?.currentSeason
      if (!season) return 0

      // 获取集数信息
      const getEpisodeEnd = (resource: any) => {
        if (!resource.tvInfo?.episodes) return -1
        const episodes = resource.tvInfo.episodes[String(season)]
        if (!episodes || episodes.end == null) return -1
        return episodes.end
      }

      const episodeA = getEpisodeEnd(a)
      const episodeB = getEpisodeEnd(b)

      // 按集数降序排列（集数大的在前面）
      return episodeB - episodeA
    })
    resourceTotal.value = res.data.total || 0
  } catch (error) {
    console.error('加载匹配资源失败:', error)
  } finally {
    resourcesLoading.value = false
  }
}

// 加载集数状态
const loadEpisodesStatus = async (refresh = false) => {
  // 只有电视剧订阅才加载集数状态
  if (!subscription.value || subscription.value.mediaType !== 'tv') {
    return
  }

  episodesLoading.value = true
  try {
    const id = Number(route.params.id)
    const res = await getEpisodesStatus(id, refresh)
    episodesStatus.value = res.data
  } catch (error) {
    console.error('加载集数状态失败:', error)
    ElMessage.error('加载集数状态失败')
  } finally {
    episodesLoading.value = false
  }
}

// 刷新集数状态
const handleRefreshEpisodes = async () => {
  episodesLoading.value = true
  try {
    const id = Number(route.params.id)
    const res = await refreshEpisodesStatus(id)
    episodesStatus.value = res.data
    ElMessage.success('集数状态已刷新')
  } catch (error) {
    console.error('刷新集数状态失败:', error)
    ElMessage.error('刷新集数状态失败')
  } finally {
    episodesLoading.value = false
  }
}

// 手动标记集数状态
const handleMarkEpisodeStatus = async (episode: number, status: string) => {
  if (!subscription.value) return
  try {
    await updateEpisodeStatus(subscription.value.id, episode, {
      status: status as 'downloaded' | 'ignored' | 'waiting',
      note: '手动标记',
    })
    ElMessage.success(`第 ${episode} 集已标记为${status === 'downloaded' ? '已下载' : status === 'ignored' ? '已忽略' : '等待中'}`)
    // 刷新集数状态
    await loadEpisodesStatus(true)
  } catch (error) {
    console.error('标记集数状态失败:', error)
    ElMessage.error('标记集数状态失败')
  }
}

// 暂停订阅
const handlePause = async () => {
  if (!subscription.value) return
  try {
    await pauseSubscription(subscription.value.id)
    ElMessage.success('订阅已暂停')
    loadSubscriptionDetail()
  } catch (error) {
    ElMessage.error('暂停订阅失败')
  }
}

// 恢复订阅
const handleResume = async () => {
  if (!subscription.value) return
  try {
    await resumeSubscription(subscription.value.id)
    ElMessage.success('订阅已恢复')
    loadSubscriptionDetail()
  } catch (error) {
    ElMessage.error('恢复订阅失败')
  }
}

// 编辑订阅
const handleEdit = () => {
  editDialogVisible.value = true
}

// 编辑成功
const handleEditSuccess = () => {
  loadSubscriptionDetail()
}

// 处理下载
const handleDownload = (resource: any) => {
  currentDownloadResource.value = resource
  downloadDialogVisible.value = true
}

// 下载成功
const handleDownloadSuccess = () => {
  ElMessage.success('下载任务已创建')
}

// 返回
// 处理手动同步
const handleManualSync = () => {
  if (!subscription.value) return
  // 默认使用订阅标题或原来的标题
  syncKeyword.value = subscription.value.title
  syncDialogVisible.value = true
}

// 执行同步
const executeSync = async () => {
  if (!subscription.value) return
  
  syncing.value = true
  try {
    const res = await syncSubscriptionPTResources(subscription.value.id, syncKeyword.value)
    
    ElMessage.success(res.data.message || '同步任务已创建')
    syncDialogVisible.value = false
    
    // 可以在这里轮询任务状态，或者简单地提示用户去查看任务列表
    // 类似于 MovieDetail，如果有 executionIds，可能需要展示进度，但为了简化，先只提示
    
  } catch (error) {
    console.error('Failed to sync resources:', error)
    ElMessage.error('创建同步任务失败')
  } finally {
    syncing.value = false
  }
}

const handleBack = () => {
  router.push('/subscriptions')
}

// 获取状态文本
const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    active: '活跃',
    paused: '暂停',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

// 格式化大小
const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 格式化日期时间
const formatDateTime = (dateString: string) => {
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

// 格式化 tv_info
const formatTvInfo = (tvInfo: any, season: number) => {
  if (!tvInfo || !tvInfo.episodes) return '-'

  const episodes = tvInfo.episodes[String(season)]
  if (!episodes) return '-'

  const { start, end } = episodes
  // 检查 start 和 end 是否有效
  if (start == null || end == null) return '-'

  if (start === end) {
    return `E${start.toString().padStart(2, '0')}`
  }

  const label = `E${start.toString().padStart(2, '0')}-E${end.toString().padStart(2, '0')}`

  // 显示完整季度标识
  if (tvInfo.is_complete_season) {
    return `${label} (完整季度)`
  }
  if (tvInfo.is_complete_series) {
    return `${label} (完整系列)`
  }

  return label
}

onMounted(async () => {
  await loadSubscriptionDetail()
  loadMatchedResources()
  // 等待订阅详情加载完成后再加载集数状态
  if (subscription.value?.mediaType === 'tv') {
    loadEpisodesStatus()
  }
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.detail-container {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.subscription-detail {
  padding: 20px;
}

.detail-row {
  display: flex;
  gap: 30px;
}

.poster {
  width: 200px;
  height: 300px;
  border-radius: 8px;
  flex-shrink: 0;
}

.info {
  flex: 1;
}

.info h2 {
  margin: 0 0 10px 0;
  font-size: 24px;
}


.original-title {
  color: var(--text-color-secondary);
  margin-bottom: 15px;
}

.meta {
  display: flex;
  gap: 12px;
  margin-bottom: 15px;
  align-items: center;
}

.season-info {
  margin-bottom: 15px;
  font-size: 15px;
  color: var(--text-color-regular);
}

.extra-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-color-secondary);
  letter-spacing: 0.02em;
}

.extra-info .dot {
  color: var(--border-color);
}

.resource-title {
  font-weight: 500;
  color: var(--text-color-primary);
}

.resource-subtitle {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-top: 4px;
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  /* 海报+信息：上下排列 */
  .detail-row {
    flex-direction: column;
  }

  .poster {
    align-self: center;
    width: 140px;
    height: 210px;
  }

  .subscription-detail {
    padding: 12px;
  }

  /* 标题 */
  .info h2 {
    font-size: 20px;
  }

  /* meta 标签行：允许折行 */
  .meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  /* 附加信息：折行，隐藏分隔点 */
  .extra-info {
    flex-wrap: wrap;
    gap: 8px;
    line-height: 1.8;
  }

  .extra-info .dot {
    display: none;
  }

  /* 卡片头部 */
  .card-header {
    flex-wrap: wrap;
    gap: 8px;
    align-items: flex-start;
  }

  .header-actions {
    flex-wrap: wrap;
    gap: 6px;
  }
}
</style>

