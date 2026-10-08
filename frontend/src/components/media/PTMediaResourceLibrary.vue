<template>
  <div class="books-page" :class="{ 'music-library': isMusic }">
    <div class="toolbar">
      <el-select v-model="siteId" clearable placeholder="全部站点" aria-label="筛选站点" @change="resetList">
        <el-option v-for="site in sites" :key="site.id" :label="site.name" :value="site.id" />
      </el-select>
      <el-input v-model="keyword" clearable :placeholder="isMusic ? '搜索专辑、歌手或资源标题' : '搜索书名或资源标题'" :aria-label="`搜索${mediaLabel}`" @keyup.enter="resetList" @clear="resetList" />
      <el-button :loading="loading" @click="resetList">搜索</el-button>
      <el-checkbox v-model="freeOnly" @change="resetList">仅免费</el-checkbox>
      <span class="muted">共 {{ total }} 个资源</span>
    </div>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <div class="book-grid" aria-live="polite" :aria-busy="loading">
      <button v-for="book in books" :key="book.id" class="book-card" @click="openBook(book)">
        <div class="cover">
          <el-image v-if="book.posterUrl" :src="getProxiedImageUrl(book.posterUrl)" :alt="book.subtitle || book.title" fit="contain" lazy>
            <template #placeholder><div class="cover-fallback cover-loading" aria-label="封面加载中"><el-icon><component :is="isMusic ? Headset : Reading" /></el-icon></div></template>
            <template #error><div class="cover-fallback"><el-icon><component :is="isMusic ? Headset : Reading" /></el-icon></div></template>
          </el-image>
          <div v-else class="cover-fallback"><el-icon><component :is="isMusic ? Headset : Reading" /></el-icon></div>
          <el-tag v-if="book.isFree" class="free-tag" type="success" size="small">免费</el-tag>
        </div>
        <div class="book-info">
          <h3 :title="book.subtitle || book.title">{{ book.subtitle || book.title }}</h3>
          <p v-if="book.subtitle" class="muted resource-title" :title="book.title">{{ book.title }}</p>
          <div class="book-meta"><span>{{ formatSize(book.sizeBytes) }}</span><span>{{ book.seeders }} 做种</span></div>
          <div class="book-meta"><span>{{ book.doubanRating ? `豆瓣 ${book.doubanRating}` : '暂无评分' }}</span><span v-if="book.publishedAt">{{ formatRelativeTime(book.publishedAt) }}</span></div>
        </div>
      </button>
      <template v-if="loading">
        <div v-for="index in (books.length ? 6 : pageSize)" :key="`skeleton-${index}`" class="book-card skeleton-card" aria-hidden="true">
          <div class="cover cover-loading" />
          <div class="book-info">
            <div class="skeleton-line cover-loading" />
            <div class="skeleton-line skeleton-short cover-loading" />
            <div class="skeleton-line skeleton-meta cover-loading" />
          </div>
        </div>
      </template>
    </div>
    <el-empty v-if="!loading && !error && books.length === 0" :description="`暂无${mediaLabel}`" />
    <div class="load-state" aria-live="polite">
      <span v-if="loading && books.length">加载中...</span>
      <span v-else-if="noMore && books.length">已加载全部内容</span>
      <el-button v-else-if="error" @click="loadBooks(books.length > 0)">重新加载</el-button>
    </div>
    <div ref="scrollTrigger" class="scroll-trigger" />

    <el-dialog v-model="detailVisible" :title="`${mediaLabel}详情`" width="min(800px, 94vw)" destroy-on-close @closed="detail = null">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="detail-heading">
            <el-image v-if="detail.posterUrl" :src="getProxiedImageUrl(detail.posterUrl)" :alt="detail.subtitle || detail.title" fit="contain">
              <template #placeholder><div class="cover-fallback cover-loading" aria-label="封面加载中"><el-icon><component :is="isMusic ? Headset : Reading" /></el-icon></div></template>
              <template #error><div class="cover-fallback"><el-icon><component :is="isMusic ? Headset : Reading" /></el-icon></div></template>
            </el-image>
            <div>
              <h2>{{ detail.subtitle || detail.title }}</h2>
              <p class="muted">{{ detail.title }}</p>
              <p>{{ formatSize(detail.sizeBytes) }} · {{ detail.seeders }} 做种 · {{ detail.leechers }} 下载</p>
              <p v-if="detail.doubanRating">豆瓣评分：{{ detail.doubanRating }}</p>
              <div class="detail-actions">
                <el-button type="primary" :loading="downloadLoading" @click="openDownload">下载</el-button>
                <el-link v-if="detail.doubanId" :href="`https://${isMusic ? 'music' : 'book'}.douban.com/subject/${detail.doubanId}/`" target="_blank" rel="noopener noreferrer">{{ isMusic ? '豆瓣音乐' : '豆瓣图书' }}</el-link>
                <el-link v-if="detail.detailUrl" :href="detail.detailUrl" target="_blank" rel="noopener noreferrer">原站点</el-link>
              </div>
            </div>
          </div>
          <el-button v-if="!detail.detailLoaded" :loading="fetching" @click="fetchDetail">获取简介</el-button>
          <div v-if="detail.description" class="description" v-html="renderSafeMarkdown(detail.description)" />
          <el-empty v-else-if="detail.detailLoaded" description="站点未提供简介" />
        </template>
      </div>
      <DownloadDialog v-model="downloadVisible" :resource="downloadResource" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onActivated, onDeactivated, onUnmounted, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Reading, Headset } from '@element-plus/icons-vue'
import { getSiteList } from '@/api/modules/site'
import { getPTResourceDetailList, getPTResourceDetail, fetchPTResourceDetail } from '@/api/modules/ptResourceDetails'
import type { PTResourceDetailItem, PTResourceDetailItemResponse } from '@/api/modules/ptResourceDetails'
import type { PTSite, PTResource } from '@/types'
import request from '@/api/request'
import { formatSize, formatRelativeTime, getProxiedImageUrl } from '@/utils'
import { renderSafeMarkdown } from '@/utils/safeHtml'
import DownloadDialog from '@/components/download/DownloadDialog.vue'

defineOptions({ name: 'PTMediaResourceLibrary' })
const props = defineProps<{ mediaType: 'book' | 'music' }>()
const isMusic = computed(() => props.mediaType === 'music')
const mediaLabel = computed(() => isMusic.value ? '音乐' : '电子书')
const sites = ref<PTSite[]>([])
const siteId = ref<number>()
const keyword = ref('')
const appliedKeyword = ref('')
const freeOnly = ref(false)
const books = ref<PTResourceDetailItem[]>([])
const page = ref(1)
const pageSize = 24
const total = ref(0)
const loading = ref(false)
const error = ref('')
const noMore = ref(false)
const scrollTrigger = ref<HTMLElement>()
let observer: IntersectionObserver | null = null
let active = true
let listVersion = 0
const detailVisible = ref(false)
const detailLoading = ref(false)
const fetching = ref(false)
const detail = ref<PTResourceDetailItemResponse | null>(null)
const downloadVisible = ref(false)
const downloadLoading = ref(false)
const downloadResource = ref<PTResource | null>(null)
let detailVersion = 0

async function openDownload() {
  if (!detail.value || downloadLoading.value) return
  const id = detail.value.id
  const version = detailVersion
  downloadLoading.value = true
  try {
    const { data } = await request.get<PTResource>(`/pt-resources/${id}`)
    if (version !== detailVersion || !detailVisible.value) return
    downloadResource.value = data
    downloadVisible.value = true
  } catch { ElMessage.error('下载资源加载失败，请重试') }
  finally { downloadLoading.value = false }
}

async function loadBooks(append = false) {
  if (append && (loading.value || noMore.value || !active)) return
  const version = ++listVersion
  const nextPage = append ? page.value + 1 : 1
  loading.value = true
  error.value = ''
  if (!append) { books.value = []; noMore.value = false }
  try {
    const { data } = await getPTResourceDetailList({ category: props.mediaType, siteId: siteId.value, keyword: appliedKeyword.value || undefined, isFree: freeOnly.value ? true : undefined, page: nextPage, pageSize })
    if (version !== listVersion) return
    const ids = new Set(books.value.map(book => book.id))
    books.value = append ? [...books.value, ...data.items.filter(book => !ids.has(book.id))] : data.items
    page.value = nextPage
    total.value = data.total
    noMore.value = books.value.length >= data.total || data.items.length < pageSize
  } catch {
    if (version === listVersion) error.value = `${mediaLabel.value}加载失败，请重新搜索或点击重新加载。`
  } finally {
    if (version === listVersion) { loading.value = false; await nextTick(); observeScroll() }
  }
}
function resetList() { appliedKeyword.value = keyword.value.trim(); void loadBooks() }

function observeScroll() {
  observer?.disconnect()
  if (!active || noMore.value || error.value || !scrollTrigger.value) return
  observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) void loadBooks(true)
  }, { rootMargin: '200px', threshold: 0 })
  observer.observe(scrollTrigger.value)
}

async function openBook(book: PTResourceDetailItem) {
  const version = ++detailVersion
  detail.value = null
  detailVisible.value = true
  detailLoading.value = true
  try {
    const { data } = await getPTResourceDetail(book.id)
    if (version === detailVersion && detailVisible.value) detail.value = data
  } catch { ElMessage.error('详情加载失败，请重试') }
  finally { if (version === detailVersion) detailLoading.value = false }
}
async function fetchDetail() {
  if (!detail.value || fetching.value) return
  const id = detail.value.id
  const version = detailVersion
  fetching.value = true
  try {
    await fetchPTResourceDetail(id)
    const { data } = await getPTResourceDetail(id)
    if (version === detailVersion && detailVisible.value) detail.value = data
  } catch { ElMessage.error('简介获取失败，请稍后重试') }
  finally { fetching.value = false }
}
onMounted(async () => {
  void loadBooks()
  try { sites.value = (await getSiteList({ page_size: 100 })).data.items }
  catch { ElMessage.error('站点列表加载失败') }
})
onActivated(() => { active = true; observeScroll() })
function stopWatching() { active = false; observer?.disconnect() }
onDeactivated(stopWatching)
onUnmounted(stopWatching)
</script>

<style scoped>
.books-page { padding: 20px; }
.toolbar, .detail-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.toolbar .el-select { width: 160px; }
.toolbar .el-input { width: 260px; }
.muted { color: var(--el-text-color-secondary); }
.load-state { text-align: center; color: var(--el-text-color-secondary); padding: 12px; }
.scroll-trigger { height: 1px; }
.book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; min-height: 120px; margin: 20px 0; }
.book-card { padding: 0; text-align: left; font: inherit; color: var(--el-text-color-primary); background: var(--el-bg-color); border: 1px solid var(--el-border-color-light); border-radius: 8px; overflow: hidden; cursor: pointer; transition: border-color .2s, box-shadow .2s; }
.book-card:hover { border-color: var(--el-color-primary); box-shadow: var(--el-box-shadow-light); }
.book-card:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 3px; }
.music-library .cover { aspect-ratio: 1; }
.music-library .detail-heading .el-image { height: 150px; }
.cover { position: relative; aspect-ratio: 2 / 3; background: var(--el-fill-color-light); }
.cover .el-image, .cover-fallback { width: 100%; height: 100%; }
.cover-fallback { display: flex; align-items: center; justify-content: center; font-size: 48px; color: var(--el-text-color-placeholder); }
.cover-loading { position: relative; overflow: hidden; background: var(--el-fill-color-light); }
.cover-loading::after { content: ''; position: absolute; inset: 0; background: linear-gradient(100deg, transparent 15%, var(--el-fill-color-blank) 50%, transparent 85%); opacity: .65; transform: translateX(-100%); animation: book-shimmer 1.8s ease-in-out infinite; }
.cover :deep(.el-image__inner), .detail-heading :deep(.el-image__inner) { animation: book-cover-in .3s ease-out; }
.skeleton-card { cursor: default; pointer-events: none; }
.skeleton-line { height: 15px; margin-bottom: 12px; border-radius: 4px; }
.skeleton-short { width: 65%; height: 12px; }
.skeleton-meta { width: 85%; height: 12px; margin: 16px 0 0; }
@keyframes book-shimmer { to { transform: translateX(100%); } }
@keyframes book-cover-in { from { opacity: 0; } to { opacity: 1; } }
.free-tag { position: absolute; top: 8px; right: 8px; }
.book-info { padding: 12px; }
.book-info h3 { font-size: 15px; margin: 0 0 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-title { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.book-meta { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--el-text-color-secondary); margin-top: 8px; }
.detail-heading { display: flex; gap: 24px; margin-bottom: 24px; overflow-wrap: anywhere; }
.detail-heading .el-image { width: 150px; height: 220px; flex-shrink: 0; }
.description { margin-top: 20px; overflow-wrap: anywhere; }
.description :deep(img) { max-width: 100%; }
@media (max-width: 600px) { .books-page { padding: 12px; } .toolbar .el-input { width: 100%; } .book-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } .detail-heading { flex-direction: column; } }
@media (prefers-reduced-motion: reduce) { .book-card { transition: none; } .cover-loading::after, .cover :deep(.el-image__inner), .detail-heading :deep(.el-image__inner) { animation: none; } }
</style>
