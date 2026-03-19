<template>
  <div class="page-container">
    <!-- 工具栏：标题 + 筛选合并为一行 -->
    <div class="page-toolbar">
      <div class="toolbar-title">
        <h2>订阅管理</h2>
        <span class="toolbar-count" v-if="total > 0">{{ total }} 个订阅</span>
      </div>
      <div class="toolbar-actions">
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="handleFilter">
          <el-option label="全部" value="" />
          <el-option label="活跃" value="active" />
          <el-option label="暂停" value="paused" />
          <el-option label="已完成" value="completed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>

        <el-select v-model="filterMediaType" placeholder="类型" clearable style="width: 110px" @change="handleFilter">
          <el-option label="全部" value="" />
          <el-option label="电视剧" value="tv" />
          <el-option label="电影" value="movie" />
        </el-select>

        <el-button :icon="Refresh" @click="handleRefresh">刷新</el-button>
      </div>
    </div>

    <!-- 订阅列表 -->
    <div v-loading="loading">
      <div v-if="subscriptions.length > 0" class="subscription-grid">
        <div
          v-for="subscription in subscriptions"
          :key="subscription.id"
          class="sub-card"
        >
          <!-- 海报区域 -->
          <div class="sub-card__poster" @click="handleViewDetail(subscription.id)">
            <el-image
              v-if="subscription.posterUrl"
              :src="getProxiedImageUrl(subscription.posterUrl)"
              fit="cover"
              class="sub-card__img"
            >
              <template #error>
                <div class="sub-card__placeholder">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="sub-card__placeholder">
              <el-icon><Picture /></el-icon>
            </div>

            <!-- 状态角标 -->
            <div class="sub-card__status-badge" :class="`is-${subscription.status}`">
              {{ getStatusText(subscription.status) }}
            </div>

            <!-- 收藏角标 -->
            <div v-if="subscription.isFavorite" class="sub-card__fav-badge">
              <el-icon><Star /></el-icon>
            </div>

          </div>

          <!-- 信息区域 -->
          <div class="sub-card__info">
            <div class="sub-card__header">
              <div class="sub-card__title" @click="handleViewDetail(subscription.id)">
                {{ subscription.title }}
              </div>
              <!-- 操作下拉菜单 -->
              <el-dropdown trigger="click" @click.stop placement="bottom-end">
                <el-icon class="sub-card__menu-btn" @click.stop><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <!-- <el-dropdown-item :icon="View" @click="handleViewDetail(subscription.id)">
                      查看详情
                    </el-dropdown-item> -->
                    <el-dropdown-item :icon="Edit" @click="handleEdit(subscription)">
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="subscription.status === 'active'"
                      :icon="VideoPause"
                      @click="handlePause(subscription.id)"
                    >
                      暂停
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-else-if="subscription.status === 'paused'"
                      :icon="VideoPlay"
                      @click="handleResume(subscription.id)"
                    >
                      恢复
                    </el-dropdown-item>
                    <el-dropdown-item
                      :icon="Delete"
                      class="danger-item"
                      @click="handleDelete(subscription.id)"
                    >
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div class="sub-card__meta">
              <el-tag size="small" :type="subscription.mediaType === 'tv' ? 'success' : 'primary'" effect="plain">
                {{ subscription.mediaType === 'tv' ? '剧' : '影' }}
              </el-tag>
              <span v-if="subscription.year" class="sub-card__year">{{ subscription.year }}</span>
              <span v-if="subscription.mediaType === 'tv' && subscription.currentSeason" class="sub-card__season">
                S{{ String(subscription.currentSeason).padStart(2, '0') }}
              </span>
            </div>

            <!-- TV 进度条 -->
            <template v-if="subscription.mediaType === 'tv' && subscription.episodesStatus">
              <div class="sub-card__progress">
                <div class="sub-card__progress-text">
                  <span>{{ getEpisodeStats(subscription).downloaded }}/{{ getEpisodeStats(subscription).total }} 集</span>
                  <span v-if="getEpisodeStats(subscription).available > 0" class="sub-card__available">
                    +{{ getEpisodeStats(subscription).available }}
                  </span>
                </div>
                <el-progress
                  :percentage="getEpisodeStats(subscription).percentage"
                  :stroke-width="4"
                  :show-text="false"
                  :color="getEpisodeStats(subscription).percentage === 100 ? '#10b981' : '#3b82f6'"
                />
              </div>
            </template>
            <template v-else-if="subscription.mediaType === 'tv'">
              <div class="sub-card__dl-count">
                <el-icon><Download /></el-icon> {{ subscription.totalDownloads }} 集
              </div>
            </template>
            <template v-else>
              <div class="sub-card__dl-count" :class="{ 'has-resource': subscription.hasResources }">
                <el-icon><DocumentChecked v-if="subscription.hasResources" /><Clock v-else /></el-icon>
                {{ subscription.hasResources ? '有可下载资源' : '暂无资源' }}
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 无限滚动触发器 -->
      <div ref="scrollTrigger" class="scroll-trigger"></div>

      <el-empty v-if="!loading && subscriptions.length === 0" description="暂无订阅" />

      <!-- 加载更多提示 -->
      <div v-if="loadingMore" class="load-more-tip">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="noMore && subscriptions.length > 0" class="load-more-tip muted">
        已显示全部 {{ total }} 个订阅
      </div>
    </div>

    <!-- 订阅编辑对话框 -->
    <SubscriptionDialog
      v-model:visible="editDialogVisible"
      :is-edit="isEditMode"
      :edit-data="editingSubscription"
      @success="handleEditSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Edit,
  Delete,
  Refresh,
  Picture,
  Star,
  Clock,
  Download,
  DocumentChecked,
  VideoPause,
  VideoPlay,
  View,
  MoreFilled,
  Loading
} from '@element-plus/icons-vue'
import {
  getSubscriptionList,
  pauseSubscription,
  resumeSubscription,
  deleteSubscription
} from '@/api/modules/subscription'
import SubscriptionDialog from '@/components/subscription/SubscriptionDialog.vue'
import type { Subscription } from '@/types/subscription'
import { getProxiedImageUrl } from '@/utils'

const router = useRouter()

const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const subscriptions = ref<Subscription[]>([])
const total = ref(0)
const filterStatus = ref('')
const filterMediaType = ref('')
const scrollTrigger = ref<HTMLElement | null>(null)

const pagination = reactive({ page: 1, pageSize: 20 })

// 编辑相关
const editDialogVisible = ref(false)
const editingSubscription = ref<Subscription | null>(null)
const isEditMode = ref(true)

// 加载订阅列表
const loadSubscriptions = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterMediaType.value) params.media_type = filterMediaType.value

    const res = await getSubscriptionList(params)
    const newItems = res.data.items || []
    subscriptions.value = append ? [...subscriptions.value, ...newItems] : newItems
    total.value = res.data.total
    noMore.value = subscriptions.value.length >= total.value
  } catch (error) {
    console.error('加载订阅列表失败:', error)
    ElMessage.error('加载订阅列表失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (loading.value || loadingMore.value || noMore.value) return
  pagination.page++
  loadSubscriptions(true)
}

// 筛选处理
const handleFilter = () => {
  pagination.page = 1
  noMore.value = false
  loadSubscriptions(false)
}

// 刷新
const handleRefresh = () => {
  pagination.page = 1
  noMore.value = false
  loadSubscriptions(false)
}

// IntersectionObserver
let observer: IntersectionObserver | null = null

const setupObserver = () => {
  if (!scrollTrigger.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting) loadMore()
    },
    { root: null, rootMargin: '300px', threshold: 0.1 }
  )
  observer.observe(scrollTrigger.value)
}

const cleanupObserver = () => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

// 查看详情
const handleViewDetail = (id: number) => {
  router.push(`/subscriptions/${id}`)
}

// 暂停订阅
const handlePause = async (id: number) => {
  try {
    await pauseSubscription(id)
    ElMessage.success('订阅已暂停')
    handleRefresh()
  } catch (error) {
    ElMessage.error('暂停订阅失败')
  }
}

// 恢复订阅
const handleResume = async (id: number) => {
  try {
    await resumeSubscription(id)
    ElMessage.success('订阅已恢复')
    handleRefresh()
  } catch (error) {
    ElMessage.error('恢复订阅失败')
  }
}

// 编辑订阅
const handleEdit = (subscription: Subscription) => {
  editingSubscription.value = subscription
  isEditMode.value = true
  editDialogVisible.value = true
}

// 编辑成功
const handleEditSuccess = () => {
  handleRefresh()
}

// 删除订阅
const handleDelete = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这个订阅吗？此操作不可撤销。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteSubscription(id)
    ElMessage.success('订阅已删除')
    handleRefresh()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除订阅失败')
    }
  }
}

// 计算TV订阅的集数统计
const getEpisodeStats = (subscription: Subscription) => {
  const episodes = subscription.episodesStatus || {}
  const values = Object.values(episodes)
  const total = values.length || subscription.totalEpisodes || 0
  const downloaded = values.filter((e: any) => e?.status === 'downloaded').length
  const available = values.filter((e: any) => e?.status === 'available').length
  const percentage = total > 0 ? Math.round((downloaded / total) * 100) : 0
  return { total, downloaded, available, percentage }
}

// 获取状态文本
const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    active: '活跃',
    paused: '暂停',
    completed: '已完成',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

onMounted(async () => {
  await loadSubscriptions()
  setTimeout(() => setupObserver(), 100)
})

onUnmounted(() => {
  cleanupObserver()
})
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-title {
  display: flex;
  align-items: baseline;
  gap: 10px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--nf-text-primary);
  }
}

.toolbar-count {
  font-size: 13px;
  color: var(--nf-text-secondary);
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

// ---- 订阅网格 ----
.subscription-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;

  @media (min-width: 1200px) {
    grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
  }
}

// ---- 单张卡片 ----
.sub-card {
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  background: var(--nf-bg-elevated);
  transition: box-shadow 0.25s, transform 0.25s;

  &:hover {
    box-shadow: var(--nf-shadow-md);
    transform: translateY(-3px);
  }
}

// ---- 海报区域 ----
.sub-card__poster {
  position: relative;
  aspect-ratio: 2 / 3;
  cursor: pointer;
  background: var(--nf-bg-overlay);
  overflow: hidden;
}

.sub-card__img {
  width: 100%;
  height: 100%;
}

.sub-card__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  color: var(--nf-text-placeholder);
}

// 状态角标（左上）
.sub-card__status-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.6;

  &.is-active   { background: rgba(103, 194, 58, 0.9);  color: #fff; }
  &.is-paused   { background: rgba(230, 162, 60, 0.9);  color: #fff; }
  &.is-completed{ background: rgba(144, 147, 153, 0.85); color: #fff; }
  &.is-cancelled{ background: rgba(245, 108, 108, 0.9); color: #fff; }
}

// 收藏角标（右上）
.sub-card__fav-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  background: #f7ba2a;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
}


// ---- 信息区域 ----
.sub-card__info {
  padding: 10px 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.sub-card__header {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.sub-card__title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--nf-text-primary);
  line-height: 1.4;
  cursor: pointer;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;

  &:hover {
    color: var(--nf-primary);
  }
}

.sub-card__menu-btn {
  flex-shrink: 0;
  font-size: 16px;
  color: var(--nf-text-secondary);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;

  &:hover {
    color: var(--nf-text-primary);
    background: var(--nf-bg-overlay);
  }
}

.sub-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.sub-card__year,
.sub-card__season {
  font-size: 12px;
  color: var(--nf-text-secondary);
}

.sub-card__progress {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sub-card__progress-text {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--nf-text-secondary);
}

.sub-card__available {
  color: var(--el-color-warning);
  font-weight: 600;
}

.sub-card__dl-count {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--nf-text-secondary);

  &.has-resource {
    color: var(--el-color-success);
  }
}

// 删除菜单项颜色
:deep(.danger-item) {
  color: var(--el-color-danger) !important;

  &:hover {
    background: var(--el-color-danger-light-9) !important;
  }
}

/* 无限滚动触发器 */
.scroll-trigger {
  height: 1px;
  width: 100%;
  visibility: hidden;
}

.load-more-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 0 4px;
  font-size: 13px;
  color: var(--nf-text-secondary);

  &.muted {
    color: var(--nf-text-placeholder);
  }
}

@media (max-width: 768px) {
  .page-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-title {
    justify-content: space-between;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }

  /* 状态/类型筛选 select 在移动端自适应宽度 */
  .toolbar-actions :deep(.el-select) {
    flex: 1;
    min-width: 0;
  }

  /* 超小屏强制单列 */
  .subscription-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)) !important;
  }
}
</style>
