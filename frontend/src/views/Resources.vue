<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">资源列表</span>
            <span v-if="pagination.total > 0" class="header-count">({{ pagination.total.toLocaleString() }})</span>
          </div>
          <div class="header-right">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索资源标题..."
              :prefix-icon="Search"
              class="search-input"
              @keyup.enter="handleSearch"
            />
            <el-button class="btn-search" :icon="Search" @click="handleSearch">搜索</el-button>
            <el-button class="btn-refresh" :icon="Refresh" @click="loadResources">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 + 批量操作 -->
      <div class="toolbar-section">
        <!-- 筛选区域 -->
        <div class="filter-bar">
          <el-form inline>
            <el-form-item label="站点">
              <el-select
                v-model="filters.siteId"
                placeholder="全部站点"
                clearable
                style="width: 150px"
                @change="handleFilterChange"
              >
                <el-option v-for="site in sites" :key="site.id" :label="site.name" :value="site.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="分类">
              <el-select
                v-model="filters.category"
                placeholder="全部分类"
                clearable
                style="width: 120px"
                @change="handleFilterChange"
              >
                <el-option label="电影" value="movie" />
                <el-option label="电视剧" value="tv" />
                <el-option label="音乐" value="music" />
                <el-option label="动漫" value="anime" />
                <el-option label="书籍" value="book" />
                <el-option label="游戏" value="game" />
                <el-option label="成人" value="adult" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
            <el-form-item label="原始分类">
              <el-select
                v-model="filters.originalCategoryId"
                placeholder="请先选择站点"
                clearable
                filterable
                style="width: 220px"
                :disabled="!filters.siteId"
                @change="handleFilterChange"
              >
                <el-option
                  v-for="cat in siteCategories"
                  :key="cat.category_id"
                  :label="cat.parent_id ? `  ├─ ${cat.name_chs || cat.name_eng || cat.category_id}` : `${cat.name_chs || cat.name_eng || cat.category_id}`"
                  :value="cat.category_id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="识别状态">
              <el-select
                v-model="filters.identificationStatus"
                placeholder="全部"
                clearable
                style="width: 120px"
                @change="handleFilterChange"
              >
                <el-option label="未识别" value="unidentified" />
                <el-option label="已识别" value="identified" />
                <el-option label="识别失败" value="failed" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <!-- 批量操作区域 -->
        <div class="batch-actions">
          <span v-if="selectedRows.length > 0" class="selection-info">
            已选择 {{ selectedRows.length }} 项
          </span>
          <el-button
            class="btn-batch-identify"
            :icon="MagicStick"
            :disabled="selectedRows.length === 0"
            @click="handleBatchIdentify"
          >
            批量识别
          </el-button>
          <el-button
            class="btn-batch-reset"
            :disabled="selectedRows.length === 0"
            @click="handleBatchResetStatus"
          >
            重置状态
          </el-button>
        </div>
      </div>

      <!-- 资源列表 -->
      <div class="table-scroll-wrapper">
      <el-table
        v-loading="loading"
        :data="resources"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="title" label="标题" min-width="300">
          <template #default="{ row }">
            <div>
              <div class="resource-title">{{ row.title }}</div>
              <div v-if="row.subtitle" class="resource-subtitle">{{ row.subtitle }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="siteName" label="站点" width="100" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.originalCategoryName"
              :content="`原始分类：${row.originalCategoryName}`"
              placement="top"
              :show-after="300"
            >
              <el-tag :type="getCategoryType(row.category)" size="small">
                {{ getCategoryLabel(row.category) }}
              </el-tag>
            </el-tooltip>
            <el-tag v-else :type="getCategoryType(row.category)" size="small">
              {{ getCategoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.sizeBytes) }}
          </template>
        </el-table-column>
        <el-table-column prop="seeders" label="做种" width="80" sortable />
        <el-table-column label="发布时间" width="160">
          <template #default="{ row }">
            {{ formatPublishedTime(row.publishedAt) }}
          </template>
        </el-table-column>
        <!-- <el-table-column label="促销" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.promotionType === 'free'" type="success" size="small">免费</el-tag>
            <el-tag v-else-if="row.promotionType === '2xfree'" type="success" size="small">
              2X免费
            </el-tag>
            <el-tag v-else-if="row.promotionType === '2x'" type="info" size="small">
              2X上传
            </el-tag>
            <el-tag v-else-if="row.promotionType === '50%'" type="warning" size="small">
              50%
            </el-tag>
            <el-tag v-else-if="row.promotionType === '2x50%'" type="warning" size="small">
              2X50%
            </el-tag>
            <el-tag v-else-if="row.promotionType === '30%'" type="warning" size="small">
              30%
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column> -->
        <el-table-column label="识别状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.identificationStatus === 'identified'" type="success" size="small">
              已识别
            </el-tag>
            <el-tag v-else-if="row.identificationStatus === 'failed'" type="danger" size="small">
              失败
            </el-tag>
            <el-tag v-else type="info" size="small" effect="plain">未识别</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="info" size="small" @click="handleViewDetail(row.id)">
              详情
            </el-button>
            <el-button link type="success" size="small" @click="handleDownload(row)">
              下载
            </el-button>
            <el-button
              v-if="row.mappingStatus !== 'identified'"
              link
              type="primary"
              size="small"
              :loading="identifyingIds.includes(row.id)"
              @click="handleIdentify(row.id)"
            >
              识别
            </el-button>
            <el-button
              v-else
              link
              type="success"
              size="small"
              @click="handleViewUnified(row)"
            >
              {{ getUnifiedLabel(row.mediaType) }}
            </el-button>

          </template>
        </el-table-column>
      </el-table>
      </div>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 下载对话框 -->
    <DownloadDialog
      v-model="downloadDialogVisible"
      :resource="currentDownloadResource"
      @success="handleDownloadSuccess"
    />

    <!-- 任务进度弹窗 -->
    <TaskProgressDialog
      v-model="taskProgressVisible"
      :task-execution-id="currentTaskExecutionId"
      @completed="handleTaskCompleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, View, MagicStick, Download } from '@element-plus/icons-vue'
import api from '@/api'
import type { PTResource } from '@/types'
import DownloadDialog from '@/components/download/DownloadDialog.vue'
import TaskProgressDialog from '@/components/TaskProgressDialog.vue'

const router = useRouter()

// 状态
const loading = ref(false)
const searchKeyword = ref('')
const resources = ref<PTResource[]>([])
const selectedRows = ref<PTResource[]>([])
const identifyingIds = ref<number[]>([])
const sites = ref<any[]>([])
const downloadDialogVisible = ref(false)
const currentDownloadResource = ref<PTResource | null>(null)
const taskProgressVisible = ref(false)
const currentTaskExecutionId = ref<number | undefined>(undefined)

// 筛选条件
const filters = reactive({
  siteId: undefined as number | undefined,
  category: undefined as string | undefined,
  originalCategoryId: undefined as string | undefined,
  isFree: undefined as boolean | undefined,
  minSeeders: undefined as number | undefined,
  identificationStatus: undefined as string | undefined
})

// 站点分类列表
const siteCategories = ref<any[]>([])

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 加载站点列表
const loadSites = async () => {
  try {
    const response = await api.site.getSiteList()
    if (response?.data) {
      sites.value = response.data.items || []
    }
  } catch (error) {
    console.error('Failed to load sites:', error)
  }
}

// 按父分类排序分类列表
const sortCategoriesByParent = (categories: any[]) => {
  if (!categories || categories.length === 0) return []

  // 分离父分类和子分类
  const parentCategories = categories.filter(cat => !cat.parent_id)
  const childCategories = categories.filter(cat => cat.parent_id)

  // 按 order 字段排序父分类
  parentCategories.sort((a, b) => (a.order || 0) - (b.order || 0))

  // 构建排序后的数组
  const sorted: any[] = []
  parentCategories.forEach(parent => {
    sorted.push(parent)
    const children = childCategories
      .filter(child => child.parent_id === parent.category_id)
      .sort((a, b) => (a.order || 0) - (b.order || 0))
    sorted.push(...children)
  })

  // 添加没有父分类的孤立子分类
  const orphanChildren = childCategories.filter(
    child => !parentCategories.find(p => p.category_id === child.parent_id)
  )
  sorted.push(...orphanChildren)

  return sorted
}

// 加载站点分类列表
const loadSiteCategories = async (siteId: number) => {
  if (!siteId) {
    siteCategories.value = []
    return
  }
  try {
    const response = await api.site.getSiteCategories(siteId)
    if (response?.data) {
      const data = response.data as any
      let categories = []
      if (data && Array.isArray(data.categories)) {
        categories = data.categories
      } else if (Array.isArray(data)) {
        categories = data
      }
      siteCategories.value = sortCategoriesByParent(categories)
    }
  } catch (error) {
    console.error('Failed to load site categories:', error)
    siteCategories.value = []
  }
}

// 监听站点变化，加载分类
watch(() => filters.siteId, (newSiteId) => {
  // 清空原始分类筛选
  filters.originalCategoryId = undefined
  if (newSiteId) {
    loadSiteCategories(newSiteId)
  } else {
    siteCategories.value = []
  }
})

// 加载资源列表
const loadResources = async () => {
  loading.value = true
  try {
    const response = await api.resource.getPTResourceList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      search: searchKeyword.value || undefined,
      ...filters
    })

    if (response?.data) {
      // 后端已在列表接口中返回映射状态，直接使用
      resources.value = response.data.items.map((item: any) => ({
        ...item,
        mappingStatus: item.hasMapping ? 'identified' : 'unidentified',
        unifiedResourceId: item.unifiedResourceId,
        mediaType: item.mediaType
      }))
      pagination.total = response.data.total || 0
    }
  } catch (error) {
    console.error('Failed to load resources:', error)
    ElMessage.error('加载资源列表失败')
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  pagination.page = 1
  loadResources()
}

// 处理筛选变化
const handleFilterChange = () => {
  pagination.page = 1
  loadResources()
}

// 处理分页变化
const handlePageChange = (page: number) => {
  pagination.page = page
  loadResources()
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  loadResources()
}

// 处理选择变化
const handleSelectionChange = (rows: PTResource[]) => {
  selectedRows.value = rows
}

// 识别单个资源
const handleIdentify = async (resourceId: number) => {
  identifyingIds.value.push(resourceId)
  try {
    await api.identification.identifyResource(resourceId)
    ElMessage.success('识别成功')
    await loadResources()
  } catch (error: any) {
    console.error('Identify failed:', error)
    ElMessage.error(error.response?.data?.message || '识别失败')
  } finally {
    identifyingIds.value = identifyingIds.value.filter((id) => id !== resourceId)
  }
}

// 批量识别
const handleBatchIdentify = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要识别的资源')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要识别选中的 ${selectedRows.value.length} 个资源吗？`,
      '批量识别',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const ptResourceIds = selectedRows.value.map((r) => r.id)

    // 根据当前的 category 过滤条件确定 mediaType
    let mediaType: 'auto' | 'movie' | 'tv' | 'music' | 'book' | 'adult' = 'auto'
    if (filters.category) {
      // 映射：PT分类 → 识别媒体类型
      const categoryMediaTypeMap: Record<string, 'movie' | 'tv' | 'music' | 'book' | 'adult'> = {
        'movie': 'movie',
        'tv': 'tv',
        'teleplay': 'tv',
        'music': 'music',
        'ebook': 'book',
        'xxx': 'adult'
      }
      mediaType = categoryMediaTypeMap[filters.category] || 'auto'
    }

    const response = await api.identification.batchIdentifyResources({
      ptResourceIds,
      mediaType,  // 传递媒体类型
      skipErrors: true
    })

    if (response && response.data) {
      // 显示任务进度弹窗
      currentTaskExecutionId.value = response.data.task_execution_id
      taskProgressVisible.value = true
      ElMessage.success(response.data.message || '批量识别任务已创建')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Batch identify failed:', error)
      ElMessage.error('创建批量识别任务失败')
    }
  }
}

// 批量重置识别状态
const handleBatchResetStatus = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要重置状态的资源')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要重置选中的 ${selectedRows.value.length} 个资源的识别状态吗？重置后它们将重新进入待识别队列。`,
      '批量重置状态',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const resourceIds = selectedRows.value.map((r) => r.id)
    await api.resource.batchResetIdentificationStatus(resourceIds)

    ElMessage.success(`成功重置 ${resourceIds.length} 个资源的识别状态`)
    await loadResources()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Batch reset status failed:', error)
      ElMessage.error('批量重置状态失败')
    }
  }
}

// 任务完成回调
const handleTaskCompleted = async () => {
  // 刷新资源列表
  await loadResources()
}

// 查看统一资源详情
const handleViewUnified = (row: any) => {
  if (row.mediaType === 'tv') {
    router.push(`/tv/${row.unifiedResourceId}`)
  } else {
    // 默认作为电影处理，或显式判断 row.mediaType === 'movie'
    router.push(`/movies/${row.unifiedResourceId}`)
  }
}

// 获取统一资源按钮标签
const getUnifiedLabel = (mediaType?: string) => {
  if (mediaType === 'tv') return '查看电视剧'
  if (mediaType === 'music') return '查看音乐'
  if (mediaType === 'anime') return '查看动漫'
  if (mediaType === 'book') return '查看书籍'
  return '查看电影'
}

// 查看资源详情
const handleViewDetail = (resourceId: number) => {
  router.push(`/resources/${resourceId}`)
}

// 处理下载
const handleDownload = (resource: PTResource) => {
  currentDownloadResource.value = resource
  downloadDialogVisible.value = true
}

// 下载任务创建成功回调
const handleDownloadSuccess = (executionId?: number) => {
  if (executionId) {
    // 显示任务进度弹窗
    currentTaskExecutionId.value = executionId
    taskProgressVisible.value = true
  } else {
    // 兼容旧版本（如果没有返回executionId）
    ElMessage.success('下载任务创建成功')
    loadResources()
  }
}

// 格式化大小
const formatSize = (bytes: number) => {
  if (!bytes) return '-'
  const gb = bytes / (1024 * 1024 * 1024)
  return `${gb.toFixed(2)} GB`
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
  loadSites()
  loadResources()
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

/* ========== Card Header 布局优化 ========== */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.header-count {
  font-size: 13px;
  color: var(--text-color-secondary);
  font-weight: normal;
  margin-left: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 240px;
}

/* ========== 工具栏区域 ========== */
.toolbar-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--bg-color-overlay);
  border-radius: var(--border-radius-sm);
  border: 1px solid var(--border-color);
}

.filter-bar {
  flex: 1;
  min-width: 300px;
}

.filter-bar :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 16px;
}

.filter-bar :deep(.el-form-item__label) {
  color: var(--text-color-secondary);
}

.filter-bar :deep(.el-select .el-select__wrapper),
.filter-bar :deep(.el-input .el-input__wrapper) {
  background-color: var(--bg-color-light);
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

.filter-bar :deep(.el-select .el-select__wrapper:hover),
.filter-bar :deep(.el-input .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-color-light) inset;
}

/* ========== 批量操作区域 ========== */
.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.selection-info {
  font-size: 13px;
  color: var(--text-color-secondary);
  padding: 0 8px;
}

/* ========== 按钮主题适配 ========== */

/* 搜索按钮 - 主色 */
.btn-search {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
}

.btn-search:hover,
.btn-search:focus {
  background-color: var(--primary-light);
  border-color: var(--primary-light);
  color: #fff;
}

/* 刷新按钮 - 次要操作 */
.btn-refresh {
  background-color: transparent;
  border-color: var(--border-color);
  color: var(--text-color-regular);
}

.btn-refresh:hover,
.btn-refresh:focus {
  background-color: var(--bg-color-overlay);
  border-color: var(--border-color-dark);
  color: var(--text-color-primary);
}

/* 批量识别按钮 - 成功色 */
.btn-batch-identify {
  background-color: var(--success-color);
  border-color: var(--success-color);
  color: #fff;
}

.btn-batch-identify:hover,
.btn-batch-identify:focus {
  background-color: #0d9466;
  border-color: #0d9466;
  color: #fff;
}

.btn-batch-identify:disabled {
  background-color: var(--bg-color-overlay);
  border-color: var(--border-color);
  color: var(--text-color-muted);
  cursor: not-allowed;
}

/* 重置状态按钮 - 警告色 */
.btn-batch-reset {
  background-color: transparent;
  border-color: var(--warning-color);
  color: var(--warning-color);
}

.btn-batch-reset:hover,
.btn-batch-reset:focus {
  background-color: var(--warning-color);
  border-color: var(--warning-color);
  color: #fff;
}

.btn-batch-reset:disabled {
  background-color: transparent;
  border-color: var(--border-color);
  color: var(--text-color-muted);
  cursor: not-allowed;
}

/* ========== 表格内容样式 ========== */
.resource-title {
  font-weight: 500;
  color: var(--text-color-primary);
}

.resource-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-color-secondary);
}


.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: var(--text-color-placeholder);
}

/* ========== Loading 遮罩样式 ========== */
:deep(.el-loading-mask) {
  background-color: var(--bg-color-light);
  opacity: 0.9;
  transition: opacity 0.2s ease-in-out;
}

:deep(.el-loading-spinner) {
  --el-loading-spinner-size: 42px;
}

:deep(.el-loading-spinner .circular) {
  width: var(--el-loading-spinner-size);
  height: var(--el-loading-spinner-size);
}

:deep(.el-loading-spinner .path) {
  stroke: var(--primary-color);
}

/* ========== 深色主题适配 ========== */
html.dark .toolbar-section {
  background-color: #221e30;
  border-color: #3d3660;
}

html.dark .btn-refresh {
  background-color: transparent;
  border-color: #4a4270;
  color: #D5CEE8;
}

html.dark .btn-refresh:hover,
html.dark .btn-refresh:focus {
  background-color: #332d4a;
  border-color: #564e80;
  color: #F0ECF9;
}

html.dark .btn-batch-identify:disabled,
html.dark .btn-batch-reset:disabled {
  background-color: #332d4a;
  border-color: #4a4270;
  color: #706590;
}

html.dark .filter-bar :deep(.el-select .el-select__wrapper),
html.dark .filter-bar :deep(.el-input .el-input__wrapper) {
  background-color: #2a2540;
  box-shadow: 0 0 0 1px #4a4270 inset;
}

/* ========== 海洋主题适配 ========== */
html.ocean .toolbar-section {
  background-color: #1a3150;
  border-color: #2a4a6e;
}

html.ocean .btn-refresh {
  background-color: transparent;
  border-color: #3a5a7e;
  color: #C5DCF0;
}

html.ocean .btn-refresh:hover,
html.ocean .btn-refresh:focus {
  background-color: #213a5c;
  border-color: #4a6a8e;
  color: #E8F4FC;
}

html.ocean .btn-batch-identify:disabled,
html.ocean .btn-batch-reset:disabled {
  background-color: #1a3150;
  border-color: #3a5a7e;
  color: #5A7A94;
}

html.ocean .filter-bar :deep(.el-select .el-select__wrapper),
html.ocean .filter-bar :deep(.el-input .el-input__wrapper) {
  background-color: #132742;
  box-shadow: 0 0 0 1px #3a5a7e inset;
}

html.ocean .selection-info {
  color: #8EAEC8;
}

/* ========== 响应式布局 ========== */
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    flex-wrap: wrap;
  }

  .search-input {
    width: 100%;
  }

  .toolbar-section {
    flex-direction: column;
  }

  .filter-bar {
    width: 100%;
  }

  .batch-actions {
    width: 100%;
    justify-content: flex-end;
  }

  /* 表格容器：右侧渐变阴影提示横向可滚动 */
  .table-scroll-wrapper {
    position: relative;
    overflow: hidden;
  }

  .table-scroll-wrapper::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 32px;
    height: 100%;
    background: linear-gradient(to left, var(--nf-bg-base, #fff) 0%, transparent 100%);
    pointer-events: none;
    z-index: 10;
  }
}
</style>
