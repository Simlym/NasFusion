<template>
  <el-dialog
    v-model="dialogVisible"
    title="资源详情"
    width="80%"
    @close="handleClose"
  >
    <!-- 顶部操作按钮 -->
    <template #header>
      <div class="dialog-header">
        <span class="dialog-title">资源详情</span>
        <div class="header-actions">
          <el-button
            type="primary"
            :icon="View"
            size="small"
            :disabled="!resource?.detailUrl"
            @click="openOriginalSite"
          >
            原站点页面
          </el-button>
          <el-button
            type="success"
            :icon="Download"
            size="small"
            @click="handleDownload"
          >
            下载
          </el-button>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="detail-content">
      <template v-if="resource">
        <!-- 基础信息 -->
        <div class="basic-info">
          <h2>{{ resource.title }}</h2>
          <p v-if="resource.subtitle" class="subtitle">{{ resource.subtitle }}</p>

          <!-- 元信息 -->
          <div class="meta-info">
            <el-tag size="small">{{ formatSize(resource.sizeBytes) }}</el-tag>
            <el-tag size="small" type="success">{{ resource.seeders }} 做种</el-tag>
            <el-tag size="small">{{ resource.leechers }} 下载</el-tag>
            <el-tag v-if="resource.isFree" size="small" type="success">FREE</el-tag>
          </div>
        </div>

        <!-- 图片列表 -->
        <div v-if="resource.imageList.length > 0" class="image-gallery">
          <el-image
            v-for="(img, index) in resource.imageList"
            :key="index"
            :src="getProxiedImageUrl(img)"
            fit="contain"
            class="gallery-image"
            :preview-src-list="resource.imageList.map(getProxiedImageUrl)"
            :initial-index="index"
          />
        </div>

        <!-- 获取详情按钮 -->
        <div v-if="!resource.detailLoaded" class="action-bar">
          <el-button
            type="primary"
            :loading="fetching"
            @click="handleFetchDetail"
          >
            {{ fetching ? '获取中...' : '获取详情' }}
          </el-button>
        </div>

        <!-- 描述（Markdown） -->
        <div v-if="resource.description" class="description">
          <h3>简介</h3>
          <div class="markdown-content" v-html="renderMarkdown(resource.description)" />
        </div>

        <!-- DMM 信息 -->
        <div v-if="resource.dmmInfo" class="dmm-info">
          <h3>DMM 信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="品番">
              {{ resource.dmmInfo.productNumber }}
            </el-descriptions-item>
            <el-descriptions-item label="导演">
              {{ resource.dmmInfo.director || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="系列">
              {{ resource.dmmInfo.series || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="制作商">
              {{ resource.dmmInfo.maker || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="厂牌">
              {{ resource.dmmInfo.label || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="演员">
              <el-tag
                v-for="actor in (resource.dmmInfo.actressList || [])"
                :key="actor"
                size="small"
                style="margin-right: 4px"
              >
                {{ actor }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="标签" :span="2">
              <el-tag
                v-for="tag in (resource.dmmInfo.keywordList || [])"
                :key="tag"
                size="small"
                type="info"
                style="margin-right: 4px; margin-bottom: 4px"
              >
                {{ tag }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- MediaInfo -->
        <div v-if="resource.mediainfo" class="mediainfo">
          <h3>MediaInfo</h3>
          <pre class="mediainfo-content">{{ resource.mediainfo }}</pre>
        </div>
      </template>

      <el-empty v-else description="资源不存在" />
    </div>

    <!-- 下载对话框 -->
    <DownloadDialog
      v-model="downloadDialogVisible"
      :resource="downloadResource"
      @success="handleDownloadSuccess"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { View, Download } from '@element-plus/icons-vue'
import api from '@/api'
import type { AdultResourceDetail } from '@/api/modules/adult'
import { getProxiedImageUrl, formatSize } from '@/utils'
import { marked } from 'marked'
import DownloadDialog from '@/components/download/DownloadDialog.vue'

interface Props {
  modelValue: boolean
  resourceId: number
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const loading = ref(false)
const fetching = ref(false)
const resource = ref<AdultResourceDetail | null>(null)
const downloadDialogVisible = ref(false)

// 转换成人资源为下载对话框需要的格式
const downloadResource = computed(() => {
  if (!resource.value) return null
  return {
    id: resource.value.id,
    title: resource.value.title,
    subtitle: resource.value.subtitle,
    sizeBytes: resource.value.sizeBytes,
    category: 'adult',
    downloadUrl: resource.value.downloadUrl,
    hasHr: false,
  }
})

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 加载资源详情
const loadResourceDetail = async () => {
  if (!props.resourceId) return

  loading.value = true
  try {
    const { data } = await api.adult.getAdultResourceDetail(props.resourceId)
    resource.value = data
  } catch (error) {
    console.error('加载资源详情失败:', error)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 获取详情（调用 API）
const handleFetchDetail = async () => {
  if (!props.resourceId) return

  fetching.value = true
  try {
    await api.adult.fetchAdultResourceDetail(props.resourceId)
    ElMessage.success('详情获取成功')

    // 重新加载详情
    await loadResourceDetail()
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  } finally {
    fetching.value = false
  }
}

// 渲染 Markdown
const renderMarkdown = (content: string) => {
  if (!content) return ''
  try {
    // 先渲染 Markdown 为 HTML
    let html: string
    const result = marked.parse(content)

    // marked.parse 可能返回 string 或 Promise<string>
    if (typeof result === 'string') {
      html = result
    } else {
      console.error('marked.parse returned unexpected type:', typeof result)
      return content
    }

    // 替换所有 img 标签的 src 为代理 URL，并添加加载类和 loading 属性
    html = html.replace(
      /<img([^>]*?)src="([^"]+)"([^>]*?)>/gi,
      (match, before, src, after) => {
        // 确保 src 是字符串
        const srcStr = String(src)
        const proxiedSrc = getProxiedImageUrl(srcStr)
        // 添加 markdown-img 类用于样式，添加 loading="lazy" 懒加载
        return `<img class="markdown-img" loading="lazy"${before}src="${proxiedSrc}"${after}>`
      }
    )

    return html
  } catch (error) {
    console.error('Markdown render error:', error)
    return content
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

// 处理下载
const handleDownload = () => {
  if (!resource.value) return
  downloadDialogVisible.value = true
}

// 下载成功回调
const handleDownloadSuccess = () => {
  ElMessage.success('下载任务创建成功')
}

// 关闭对话框
const handleClose = () => {
  resource.value = null
}

// 为 Markdown 中的图片添加加载完成监听
const setupImageLoadListeners = () => {
  nextTick(() => {
    const images = document.querySelectorAll('.markdown-content .markdown-img')
    images.forEach((img) => {
      const imgElement = img as HTMLImageElement

      // 如果图片已经加载完成（来自缓存）
      if (imgElement.complete) {
        imgElement.setAttribute('data-loaded', 'true')
      } else {
        // 监听加载完成事件
        imgElement.addEventListener('load', () => {
          imgElement.setAttribute('data-loaded', 'true')
        }, { once: true })

        // 监听加载失败事件
        imgElement.addEventListener('error', () => {
          // 即使失败也显示（避免一直显示加载状态）
          imgElement.setAttribute('data-loaded', 'true')
        }, { once: true })
      }
    })
  })
}

// 监听对话框打开（只需这一个 watch 即可处理所有情况）
watch(dialogVisible, (newValue) => {
  if (newValue && props.resourceId) {
    loadResourceDetail()
  }
})

// 监听资源数据变化，设置图片加载监听
watch(resource, (newValue) => {
  if (newValue?.description) {
    setupImageLoadListeners()
  }
})
</script>

<style scoped>
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 40px;
}

.dialog-title {
  font-size: 18px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.detail-content {
  max-height: 70vh;
  overflow-y: auto;
}

.basic-info {
  margin-bottom: 24px;
}

.basic-info h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: var(--el-text-color-primary);
}

.subtitle {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.meta-info {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.image-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.gallery-image {
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

.action-bar {
  margin-bottom: 24px;
  text-align: center;
}

.description,
.dmm-info,
.mediainfo {
  margin-bottom: 24px;
}

.description h3,
.dmm-info h3,
.mediainfo h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
  color: var(--el-text-color-primary);
}

.markdown-content {
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.markdown-content :deep(img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 8px 0;
  display: block;
  height: auto;
}

/* Markdown 图片渐进式加载效果 */
.markdown-content :deep(.markdown-img) {
  /* 初始状态：透明 + 轻微模糊 */
  opacity: 0;
  filter: blur(8px);
  transform: scale(0.98);
  transition: opacity 0.6s ease-out,
              filter 0.6s ease-out,
              transform 0.6s ease-out;

  /* 加载中的背景占位 */
  background: linear-gradient(
    90deg,
    var(--el-fill-color-light) 0%,
    var(--el-fill-color) 50%,
    var(--el-fill-color-light) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  min-height: 100px;
}

/* 图片加载完成后的状态 */
.markdown-content :deep(.markdown-img[data-loaded="true"]) {
  opacity: 1;
  filter: blur(0);
  transform: scale(1);
  background: none;
  animation: none;
}

/* 骨架屏闪烁动画 */
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.mediainfo-content {
  background-color: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
