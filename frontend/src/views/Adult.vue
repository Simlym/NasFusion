<template>
  <div class="page-container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="filters.siteId"
          placeholder="全部站点"
          clearable
          style="width: 140px; margin-right: 12px"
          @change="handleSiteChange"
        >
          <el-option v-for="site in sites" :key="site.id" :label="site.name" :value="site.id" />
        </el-select>
        <el-select
          v-model="filters.originalCategoryId"
          placeholder="全部分类"
          clearable
          filterable
          style="width: 200px; margin-right: 12px"
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
        <span class="total-count">共 {{ pagination.total }} 个资源</span>
      </div>
    </div>

    <!-- 资源卡片网格 -->
    <div v-loading="loading && resources.length === 0" class="resources-grid">
      <el-card
        v-for="resource in resources"
        :key="resource.id"
        class="resource-card"
        :body-style="{ padding: '0px' }"
        shadow="hover"
        @click="handleViewDetail(resource)"
      >
        <!-- 主图 -->
        <div class="resource-poster">
          <el-image
            v-if="resource.posterUrl || resource.imageList?.[0]"
            :src="getProxiedImageUrl(resource.posterUrl || resource.imageList?.[0])"
            fit="cover"
            lazy
            class="poster-image"
          >
            <template #placeholder>
              <div class="image-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
              </div>
            </template>
            <template #error>
              <div class="image-slot">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          <div v-else class="image-slot">
            <el-icon><Picture /></el-icon>
          </div>

          <!-- 促销标签 -->
          <!-- <el-tag v-if="resource.isFree" type="success" class="promo-tag">FREE</el-tag>
          <el-tag v-else-if="resource.promotionType" type="warning" class="promo-tag">
            {{ resource.promotionType }}
          </el-tag> -->
        </div>

        <!-- 标题 -->
        <div class="resource-info">
          <div class="resource-title" :title="resource.title">
            {{ resource.title }}
          </div>

          <!-- 副标题 -->
          <div v-if="resource.subtitle" class="resource-subtitle" :title="resource.subtitle">
            {{ resource.subtitle }}
          </div>

          <!-- 元信息 -->
          <div class="resource-meta">
            <div class="meta-left">
              <span class="meta-item">
                <el-icon><Document /></el-icon>
                {{ formatSize(resource.sizeBytes) }}
              </span>
              <span class="meta-item">
                <el-icon><Upload /></el-icon>
                {{ resource.seeders }}
              </span>
              <span v-if="resource.leechers > 0" class="meta-item">
                <el-icon><DownloadIcon /></el-icon>
                {{ resource.leechers }}
              </span>
            </div>
            <div v-if="resource.publishedAt" class="meta-right">
              <el-icon><Clock /></el-icon>
              {{ formatRelativeTime(resource.publishedAt) }}
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 加载更多指示器 -->
    <div v-if="loadingMore" class="loading-more">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <!-- 已加载全部 -->
    <div v-if="noMore && resources.length > 0" class="no-more">
      已加载全部内容
    </div>

    <!-- 无限滚动触发器 -->
    <div ref="scrollTrigger" class="scroll-trigger"></div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && resources.length === 0" description="暂无限制级资源">
      <el-button type="primary" @click="$router.push('/resources')">
        去查看PT资源
      </el-button>
    </el-empty>

    <!-- 详情对话框 -->
    <AdultResourceDetailDialog
      v-model="detailDialogVisible"
      :resource-id="selectedResourceId"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, defineOptions } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Loading, Clock, Upload, Download as DownloadIcon, Document } from '@element-plus/icons-vue'
import api from '@/api'
import type { AdultResource } from '@/api/modules/adult'
import { getProxiedImageUrl, formatSize, formatRelativeTime } from '@/utils'
import AdultResourceDetailDialog from '@/components/AdultResourceDetailDialog.vue'

// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'AdultView'
})

// 站点和分类数据
interface PTSite {
  id: number
  name: string
  type: string
}
const sites = ref<PTSite[]>([])
const siteCategories = ref<any[]>([])

// 筛选条件
const filters = reactive({
  siteId: undefined as number | undefined,
  originalCategoryId: undefined as string | undefined
})

// 数据
const loading = ref(false)
const loadingMore = ref(false)
const resources = ref<AdultResource[]>([])
const pagination = reactive({
  total: 0,
  page: 1,
  pageSize: 20
})

// 详情对话框
const detailDialogVisible = ref(false)
const selectedResourceId = ref<number>(0)

// 无限滚动
const scrollTrigger = ref<HTMLElement>()
const noMore = ref(false)

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

  const parentCategories = categories.filter(cat => !cat.parent_id)
  const childCategories = categories.filter(cat => cat.parent_id)

  parentCategories.sort((a, b) => (a.order || 0) - (b.order || 0))

  const sorted: any[] = []
  parentCategories.forEach(parent => {
    sorted.push(parent)
    const children = childCategories
      .filter(child => child.parent_id === parent.category_id)
      .sort((a, b) => (a.order || 0) - (b.order || 0))
    sorted.push(...children)
  })

  const orphanChildren = childCategories.filter(
    child => !parentCategories.find(p => p.category_id === child.parent_id)
  )
  sorted.push(...orphanChildren)

  return sorted
}

// 加载站点分类（仅加载成人分类）
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
      // 只保留成人分类，然后排序
      const adultCategories = categories.filter((cat: any) => cat.mapped_category === 'adult')
      siteCategories.value = sortCategoriesByParent(adultCategories)
    }
  } catch (error) {
    console.error('Failed to load site categories:', error)
    siteCategories.value = []
  }
}

// 处理站点变化
const handleSiteChange = (siteId: number | undefined) => {
  filters.originalCategoryId = undefined
  if (siteId) {
    loadSiteCategories(siteId)
  } else {
    siteCategories.value = []
  }
  loadResources()
}

// 处理筛选变化
const handleFilterChange = () => {
  loadResources()
}

// 加载资源列表
const loadResources = async (isLoadMore = false) => {
  try {
    if (isLoadMore) {
      loadingMore.value = true
    } else {
      loading.value = true
      pagination.page = 1
      resources.value = []
      noMore.value = false
    }

    const { data } = await api.adult.getAdultResources({
      page: pagination.page,
      pageSize: pagination.pageSize,
      siteId: filters.siteId,
      originalCategoryId: filters.originalCategoryId
    })

    if (isLoadMore) {
      resources.value.push(...data.items)
    } else {
      resources.value = data.items
    }

    pagination.total = data.total

    // 检查是否已加载全部
    if (resources.value.length >= data.total) {
      noMore.value = true
    }
  } catch (error) {
    console.error('加载成人资源失败:', error)
    ElMessage.error('加载失败，请稍后重试')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

// 查看详情
const handleViewDetail = (resource: AdultResource) => {
  selectedResourceId.value = resource.id
  detailDialogVisible.value = true
}

// 无限滚动处理
const handleScroll = async () => {
  if (!scrollTrigger.value) return

  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !loadingMore.value && !noMore.value) {
      pagination.page++
      loadResources(true)
    }
  }, { threshold: 0.1 })

  observer.observe(scrollTrigger.value)

  // 保存 observer 引用以便清理
  ;(window as any)._scrollObserver = observer
}

// 生命周期
onMounted(() => {
  loadSites()
  loadResources()
  nextTick(() => {
    handleScroll()
  })
})

onUnmounted(() => {
  // 清理 observer
  if ((window as any)._scrollObserver) {
    ;(window as any)._scrollObserver.disconnect()
  }
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-count {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

/* 资源卡片网格 */
.resources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 20px;
}

.resource-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.resource-card:hover {
  transform: translateY(-4px);
}

.resource-poster {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 比例 */
  background-color: var(--el-fill-color-light);
  overflow: hidden;
}

.poster-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.image-loading,
.image-slot {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--el-text-color-placeholder);
  background-color: var(--el-fill-color-lighter);
}

.promo-tag {
  position: absolute;
  top: 8px;
  right: 8px;
}

.resource-info {
  padding: 12px;
}

.resource-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  min-height: 40px;
  margin-bottom: 4px;
}

.resource-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
}

.resource-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.meta-left {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-right {
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item .el-icon {
  font-size: 14px;
}

/* 加载状态 */
.loading-more,
.no-more {
  text-align: center;
  padding: 20px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.scroll-trigger {
  height: 1px;
}
</style>
