<template>
  <div class="page-container">
    <el-page-header @back="handleBack">
      <template #content>
        <span class="page-title">电影详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" class="movie-detail-container">
      <!-- 电影信息卡片 -->
      <el-card v-if="movie" class="movie-info-card">
        <div class="movie-header">
          <!-- 左侧：海报 -->
          <div class="movie-poster-section">
            <el-image
              v-if="movie.posterUrl"
              :src="getProxiedImageUrl(movie.posterUrl)"
              fit="cover"
              class="movie-poster"
            >
              <template #error>
                <div class="image-slot">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="image-slot">
              <el-icon><Picture /></el-icon>
            </div>
          </div>

          <!-- 右侧：详细信息 -->
          <div class="movie-info-section">
            <h1 class="movie-title">{{ movie.title }}</h1>
            <h2 v-if="movie.originalTitle" class="movie-original-title">
              {{ movie.originalTitle }}
            </h2>

            <div class="movie-meta-row">
              <div v-if="movie.year" class="meta-item">
                <el-icon><Calendar /></el-icon>
                <span>{{ movie.year }}</span>
              </div>
              <div v-if="movie.runtime" class="meta-item">
                <el-icon><Clock /></el-icon>
                <span>{{ movie.runtime }} 分钟</span>
              </div>
            </div>

            <!-- 评分 + 演职人员 合并行 -->
            <div class="rating-cast-row">
              <!-- 评分区 -->
              <div v-if="movie.ratingDouban || movie.ratingTmdb || movie.ratingImdb" class="rating-cards">
                <div v-if="movie.ratingDouban" class="rating-card douban">
                  <div class="rating-source">豆瓣</div>
                  <div class="rating-score">{{ movie.ratingDouban.toFixed(1) }}</div>
                  <div v-if="movie.votesDouban" class="rating-votes">
                    <el-icon><User /></el-icon>
                    {{ formatVotes(movie.votesDouban) }} 评价
                  </div>
                </div>
                <div v-if="movie.ratingTmdb" class="rating-card tmdb">
                  <div class="rating-source">TMDB</div>
                  <div class="rating-score">{{ movie.ratingTmdb.toFixed(1) }}</div>
                  <div v-if="movie.votesTmdb" class="rating-votes">
                    <el-icon><User /></el-icon>
                    {{ formatVotes(movie.votesTmdb) }} 评价
                  </div>
                </div>
                <div v-if="movie.ratingImdb" class="rating-card imdb">
                  <div class="rating-source">IMDB</div>
                  <div class="rating-score">{{ movie.ratingImdb.toFixed(1) }}</div>
                  <div v-if="movie.votesImdb" class="rating-votes">
                    <el-icon><User /></el-icon>
                    {{ formatVotes(movie.votesImdb) }} 评价
                  </div>
                </div>
              </div>

              <!-- 分隔符：评分与人物 -->
              <span v-if="(movie.ratingDouban || movie.ratingTmdb || movie.ratingImdb) && (movie.directors?.length || movie.actors?.length)" class="cast-separator">·</span>

              <!-- 导演区 -->
              <div v-if="movie.directors && movie.directors.length" class="cast-inline-group">
                <span class="cast-inline-label">导演</span>
                <div class="cast-inline-list">
                  <div v-for="director in movie.directors" :key="director.id" class="cast-inline-item" @click="goToPerson(director.id)">
                    <div class="cast-inline-avatar-wrap">
                      <img
                        v-if="getProxiedImageUrl(director.thumb_url)"
                        :src="getProxiedImageUrl(director.thumb_url)"
                        class="cast-inline-avatar-img"
                        loading="lazy"
                        @load="($event.target as HTMLImageElement).classList.add('loaded')"
                      />
                      <span v-else class="cast-inline-avatar-fallback">{{ director.name?.charAt(0) }}</span>
                      <div class="avatar-skeleton"></div>
                    </div>
                    <span class="cast-inline-name" :title="director.name">{{ director.name }}</span>
                  </div>
                </div>
              </div>

              <!-- 分隔符：导演与主演 -->
              <span v-if="movie.directors?.length && movie.actors?.length" class="cast-separator">·</span>

              <!-- 主演区 -->
              <div v-if="movie.actors && movie.actors.length" class="cast-inline-group cast-inline-actors">
                <span class="cast-inline-label">主演</span>
                <div class="cast-inline-list">
                  <div v-for="actor in movie.actors.slice(0, 8)" :key="actor.id" class="cast-inline-item" @click="goToPerson(actor.id)">
                    <div class="cast-inline-avatar-wrap">
                      <img
                        v-if="getProxiedImageUrl(actor.thumb_url)"
                        :src="getProxiedImageUrl(actor.thumb_url)"
                        class="cast-inline-avatar-img"
                        loading="lazy"
                        @load="($event.target as HTMLImageElement).classList.add('loaded')"
                      />
                      <span v-else class="cast-inline-avatar-fallback">{{ actor.name?.charAt(0) }}</span>
                      <div class="avatar-skeleton"></div>
                    </div>
                    <span class="cast-inline-name" :title="actor.name">{{ actor.name }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="movie.overview" class="movie-overview">
              <h3>剧情简介</h3>
              <p>{{ movie.overview }}</p>
            </div>

            <div class="movie-ids-row">
              <div class="movie-ids">
                <el-tag
                  v-if="movie.imdbId"
                  size="small"
                  class="id-link-tag"
                  @click="openIdLink('imdb', movie.imdbId)"
                >
                  <el-icon class="id-icon"><Link /></el-icon>
                  IMDB: {{ movie.imdbId }}
                </el-tag>
                <div v-if="movie.tmdbId" class="id-group">
                  <el-tag
                    size="small"
                    type="success"
                    class="id-link-tag left-tag"
                    @click="openIdLink('tmdb_movie', movie.tmdbId)"
                  >
                    <el-icon class="id-icon"><Link /></el-icon>
                    TMDB: {{ movie.tmdbId }}
                  </el-tag>
                  <el-tag
                    size="small"
                    type="success"
                    class="right-tag"
                    :class="{ 'is-loading': refreshingTmdb }"
                    @click="handleRefreshMetadata('tmdb')"
                  >
                    <el-icon :class="{ 'is-loading': refreshingTmdb }"><Refresh /></el-icon>
                  </el-tag>
                </div>
                <div v-if="movie.doubanId" class="id-group">
                  <el-tag
                    size="small"
                    type="warning"
                    class="id-link-tag left-tag"
                    @click="openIdLink('douban', movie.doubanId)"
                  >
                    <el-icon class="id-icon"><Link /></el-icon>
                    豆瓣: {{ movie.doubanId }}
                  </el-tag>
                  <el-tag
                    size="small"
                    type="warning"
                    class="right-tag"
                    :class="{ 'is-loading': refreshingDouban }"
                    @click="handleRefreshMetadata('douban')"
                  >
                    <el-icon :class="{ 'is-loading': refreshingDouban }"><Refresh /></el-icon>
                  </el-tag>
                </div>
              </div>
              <el-button
                type="primary"
                :icon="Edit"
                size="small"
                @click="handleOpenEditDialog"
              >
                编辑信息
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- PT资源列表卡片 -->
      <el-card v-if="movie" class="pt-resources-card">
        <template #header>
          <div class="card-header">
            <span>关联的PT资源 ({{ ptTotal }})</span>
            <div class="header-actions">
              <el-button-group>
                <el-button
                  type="success"
                  :loading="syncing"
                  size="small"
                  @click="handleSyncPTResources"
                >
                  手动同步资源
                </el-button>
              </el-button-group>
              <el-tag v-if="hasFreeResource" type="success" size="small" style="margin-left: 10px">
                有免费资源
              </el-tag>
              <el-select
                v-model="sortBy"
                placeholder="排序方式"
                size="small"
                style="width: 150px; margin-left: 10px"
                @change="handleSortChange"
              >
                <el-option label="做种数从高到低" value="seeders" />
                <el-option label="大小从大到小" value="size" />
                <el-option label="发布时间从新到旧" value="publishedAt" />
                <el-option label="优先显示免费" value="free" />
              </el-select>
            </div>
          </div>
        </template>

        <el-table :data="sortedPTResources" style="width: 100%">
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
          <el-table-column prop="siteName" label="站点" width="120" />
          <el-table-column label="大小" width="100">
            <template #default="{ row }">
              {{ row.sizeHumanReadable }}
            </template>
          </el-table-column>
          <el-table-column prop="seeders" label="做种" width="80" sortable />
          <el-table-column prop="leechers" label="下载" width="80" sortable />
          <el-table-column label="促销" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.isFree && row.isDoubleUpload" type="success" size="small">
                2X免费
              </el-tag>
              <el-tag v-else-if="row.isFree" type="success" size="small"> 免费 </el-tag>
              <el-tag v-else-if="row.isDiscount" type="warning" size="small">
                {{ row.promotionType }}
              </el-tag>
              <el-tag v-else-if="row.isDoubleUpload" type="info" size="small"> 2X上传 </el-tag>
              <el-tag v-else type="info" size="small" effect="plain">无促销</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="发布时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.publishedAt) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="handleDownload(row)">
                下载
              </el-button>
              <el-button
                v-if="row.detailsUrl"
                link
                type="info"
                size="small"
                @click="handleOpenLink(row.detailsUrl)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="ptResources.length === 0"
          description="暂无关联的PT资源"
          style="margin-top: 20px"
        />

        <!-- 分页组件 -->
        <el-pagination
          v-if="ptTotalPages > 1"
          v-model:current-page="ptCurrentPage"
          v-model:page-size="ptPageSize"
          :page-sizes="[20, 50, 100]"
          :total="ptTotal"
          layout="total, sizes, prev, pager, next, jumper"
          style="margin-top: 20px; justify-content: center"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </el-card>
    </div>

    <!-- 下载对话框 -->
    <DownloadDialog
      v-model="downloadDialogVisible"
      :resource="selectedResource"
      :unified-table-name="'unified_movies'"
      :unified-resource-id="movie?.id"
      @success="handleDownloadSuccess"
    />

    <!-- 任务进度弹窗 -->
    <TaskProgressDialog
      v-model="taskProgressVisible"
      :task-execution-id="currentTaskExecutionId"
      @completed="handleTaskCompleted"
    />

    <!-- 编辑电影信息对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑电影信息"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        label-width="100px"
        label-position="right"
      >
        <!-- 外部ID -->
        <el-divider content-position="left">外部ID</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="IMDB ID" prop="imdbId">
              <el-input v-model="editForm.imdbId" placeholder="如: tt1234567" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="TMDB ID" prop="tmdbId">
              <el-input-number
                v-model="editForm.tmdbId"
                :min="1"
                :controls="false"
                placeholder="如: 1234567"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="豆瓣 ID" prop="doubanId">
              <el-input v-model="editForm.doubanId" placeholder="如: 12345678" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="标题" prop="title">
          <el-input v-model="editForm.title" placeholder="电影标题" />
        </el-form-item>
        <el-form-item label="原始标题" prop="originalTitle">
          <el-input v-model="editForm.originalTitle" placeholder="原始标题（外文）" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="年份" prop="year">
              <el-input-number
                v-model="editForm.year"
                :min="1800"
                :max="2100"
                :controls="false"
                placeholder="年份"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="时长" prop="runtime">
              <el-input-number
                v-model="editForm.runtime"
                :min="1"
                :controls="false"
                placeholder="分钟"
                style="width: 100%"
              >
                <template #suffix>分钟</template>
              </el-input-number>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分级" prop="certification">
              <el-input v-model="editForm.certification" placeholder="如: PG-13" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 评分信息 -->
        <el-divider content-position="left">评分信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="豆瓣评分">
              <el-input-number
                v-model="editForm.ratingDouban"
                :min="0"
                :max="10"
                :precision="1"
                :step="0.1"
                :controls="false"
                placeholder="0-10"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="豆瓣投票数">
              <el-input-number
                v-model="editForm.votesDouban"
                :min="0"
                :controls="false"
                placeholder="投票人数"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="TMDB评分">
              <el-input-number
                v-model="editForm.ratingTmdb"
                :min="0"
                :max="10"
                :precision="1"
                :step="0.1"
                :controls="false"
                placeholder="0-10"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="TMDB投票数">
              <el-input-number
                v-model="editForm.votesTmdb"
                :min="0"
                :controls="false"
                placeholder="投票人数"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="IMDB评分">
              <el-input-number
                v-model="editForm.ratingImdb"
                :min="0"
                :max="10"
                :precision="1"
                :step="0.1"
                :controls="false"
                placeholder="0-10"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="IMDB投票数">
              <el-input-number
                v-model="editForm.votesImdb"
                :min="0"
                :controls="false"
                placeholder="投票人数"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 分类信息 -->
        <el-divider content-position="left">分类信息</el-divider>
        <el-form-item label="类型" prop="genres">
          <el-select
            v-model="editForm.genres"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入类型"
            style="width: 100%"
          >
            <el-option
              v-for="genre in commonGenres"
              :key="genre"
              :label="genre"
              :value="genre"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="国家/地区" prop="countries">
          <el-select
            v-model="editForm.countries"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入国家/地区"
            style="width: 100%"
          >
            <el-option
              v-for="country in commonCountries"
              :key="country"
              :label="country"
              :value="country"
            />
          </el-select>
        </el-form-item>

        <!-- 内容描述 -->
        <el-divider content-position="left">内容描述</el-divider>
        <el-form-item label="简介" prop="overview">
          <el-input
            v-model="editForm.overview"
            type="textarea"
            :rows="4"
            placeholder="电影简介"
          />
        </el-form-item>
        <el-form-item label="宣传语" prop="tagline">
          <el-input v-model="editForm.tagline" placeholder="电影宣传语" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveMovie">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Picture, Calendar, Clock, Star, Download, Link, Refresh, User, Edit } from '@element-plus/icons-vue'
import api from '@/api'
import type { UnifiedMovieWithPTResources, PTResource } from '@/types'
import type { MovieUpdateData } from '@/api/modules/movie'
import DownloadDialog from '@/components/download/DownloadDialog.vue'
import TaskProgressDialog from '@/components/TaskProgressDialog.vue'
import { getProxiedImageUrl } from '@/utils'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const refreshing = ref(false)
const syncing = ref(false)
const refreshingTmdb = ref(false)
const refreshingDouban = ref(false)
const movie = ref<UnifiedMovieWithPTResources | null>(null)
const ptResources = ref<PTResource[]>([])
const sortBy = ref('publishedAt')  // 默认按发布时间排序（与后端一致）

// PT资源分页
const ptCurrentPage = ref(1)
const ptPageSize = ref(20)
const ptTotal = ref(0)
const ptTotalPages = ref(0)

// 下载相关
const downloadDialogVisible = ref(false)
const selectedResource = ref<PTResource | null>(null)
const taskProgressVisible = ref(false)
const currentTaskExecutionId = ref<number | undefined>(undefined)

// 编辑相关
const editDialogVisible = ref(false)
const saving = ref(false)
const editFormRef = ref()
const editForm = reactive<MovieUpdateData>({
  imdbId: null,
  tmdbId: null,
  doubanId: null,
  title: '',
  originalTitle: null,
  year: null,
  runtime: null,
  certification: null,
  ratingDouban: null,
  ratingTmdb: null,
  ratingImdb: null,
  votesDouban: null,
  votesTmdb: null,
  votesImdb: null,
  genres: [],
  countries: [],
  overview: null,
  tagline: null
})

// 常用类型选项
const commonGenres = [
  '剧情', '喜剧', '动作', '爱情', '科幻', '悬疑', '惊悚', '恐怖',
  '犯罪', '动画', '冒险', '奇幻', '战争', '传记', '历史', '音乐',
  '歌舞', '家庭', '儿童', '纪录片', '短片', '西部', '黑色电影'
]

// 常用国家/地区选项
const commonCountries = [
  '中国大陆', '中国香港', '中国台湾', '美国', '日本', '韩国',
  '英国', '法国', '德国', '意大利', '西班牙', '印度', '泰国',
  '加拿大', '澳大利亚', '俄罗斯', '巴西', '墨西哥'
]

// 加载电影详情
const loadMovieDetail = async (skipAutoRefresh = false) => {
  loading.value = true
  try {
    const movieId = Number(route.params.id)
    const response = await api.movie.getMovieDetail(movieId, {
      ptPage: ptCurrentPage.value,
      ptPageSize: ptPageSize.value
    })

    // 响应拦截器返回完整的 response 对象，需要访问 response.data
    if (response?.data && response.data.id) {
      movie.value = response.data as any
      const resources = response.data.ptResources || []
      const pagination = response.data.ptResourcesPagination

      // 更新分页信息
      if (pagination) {
        ptTotal.value = pagination.total
        ptTotalPages.value = pagination.totalPages
      }

      // 调试：检查返回的数据格式
      // console.log('Initial PT Resources:', resources)
      // console.log('Is Array:', Array.isArray(resources))
      if (resources.length > 0) {
        // console.log('First resource:', resources[0])
      }

      ptResources.value = resources

      // ⚠️ 已禁用自动刷新功能，避免频繁请求PT站点API
      // 如需刷新，请手动点击"刷新资源信息"按钮
      // if (!skipAutoRefresh) {
      //   await checkAndAutoRefresh()
      // }
    } else {
      console.error('Invalid response format:', response)
      ElMessage.error('返回数据格式错误')
    }
  } catch (error) {
    console.error('Failed to load movie detail:', error)
    ElMessage.error('加载电影详情失败')
  } finally {
    loading.value = false
  }
}

// 检查并自动刷新过期资源
const checkAndAutoRefresh = async () => {
  if (!ptResources.value || ptResources.value.length === 0) return

  // 检查资源是否过期（30分钟 = 1800000毫秒）
  const EXPIRY_THRESHOLD = 30 * 60 * 1000

  // 获取当前UTC时间（关键修复：使用 Date.now() 获取正确的UTC时间戳）
  const nowUtc = Date.now()

  const hasExpiredResource = ptResources.value.some((resource) => {
    if (!resource.lastCheckAt) {
      // 从未检查过，需要刷新
      // console.log(`资源 ${resource.id} (${resource.title.substring(0, 50)}) 从未检查过，需要刷新`)
      return true
    }

    // 后端已返回带时区信息的 ISO 8601 格式（如 "2025-11-22T18:30:00+08:00"）
    // 浏览器 new Date() 会自动正确解析
    const lastCheckDate = new Date(resource.lastCheckAt)
    const lastCheckTime = lastCheckDate.getTime()
    const timeSinceLastCheck = nowUtc - lastCheckTime
    const isExpired = timeSinceLastCheck > EXPIRY_THRESHOLD

    // 调试日志
    // console.log(`资源 ${resource.id}:`)
    // console.log(`  标题: ${resource.title.substring(0, 50)}...`)
    // console.log(`  上次检查时间: ${resource.lastCheckAt}`)
    // console.log(`  解析后: ${lastCheckDate.toISOString()}`)
    // console.log(`  距离现在: ${minutesAgo} 分钟`)
    // console.log(`  是否过期 (>30分钟): ${isExpired}`)

    return isExpired
  })

  if (hasExpiredResource) {
    // console.log('检测到过期资源，启动后台自动刷新...')

    // 在后台异步执行刷新，不阻塞页面加载
    handleRefreshResources(true).catch((error) => {
      console.warn('自动刷新失败:', error)
    })

    // 立即返回，不等待刷新完成
  } else {
    // console.log('所有资源都在有效期内，无需刷新')
  }
}

// 是否有免费资源
const hasFreeResource = computed(() => {
  return ptResources.value.some((r) => r.isFree)
})

// 排序后的PT资源
const sortedPTResources = computed(() => {
  const resources = [...ptResources.value]

  switch (sortBy.value) {
    case 'seeders':
      return resources.sort((a, b) => b.seeders - a.seeders)
    case 'size':
      return resources.sort((a, b) => b.sizeBytes - a.sizeBytes)
    case 'publishedAt':
      return resources.sort((a, b) => {
        const aTime = a.publishedAt ? new Date(a.publishedAt).getTime() : 0
        const bTime = b.publishedAt ? new Date(b.publishedAt).getTime() : 0
        return bTime - aTime
      })
    case 'free':
      return resources.sort((a, b) => {
        const aFree = a.isFree ? 1 : 0
        const bFree = b.isFree ? 1 : 0
        if (bFree !== aFree) return bFree - aFree
        return b.seeders - a.seeders
      })
    default:
      return resources
  }
})

// 处理排序变化
const handleSortChange = () => {
  // 已通过计算属性自动更新
}

// 处理分页变化
const handlePageChange = (page: number) => {
  ptCurrentPage.value = page
  loadMovieDetail(true) // 跳过自动刷新
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  ptPageSize.value = size
  ptCurrentPage.value = 1 // 重置到第一页
  loadMovieDetail(true) // 跳过自动刷新
}

// 跳转到人员详情
const goToPerson = (personId: number) => {
  if (!personId || isNaN(personId)) {
    ElMessage.warning('该人员尚未关联，无法跳转')
    return
  }
  router.push(`/person/${personId}`)
}

// 刷新元数据（从 TMDB 或豆瓣）
const handleRefreshMetadata = async (source: string) => {
  if (!movie.value) return

  const loadingRef = source === 'tmdb' ? refreshingTmdb : refreshingDouban
  loadingRef.value = true

  try {
    const response = await api.movie.refreshMovieMetadata(movie.value.id, source)
    const result = response.data
    if (result) {
      const fieldCount = result.updatedFields?.length || 0
      if (fieldCount > 0) {
        ElMessage.success(`${result.message}，更新了 ${fieldCount} 个字段`)
      } else {
        ElMessage.info(`${result.message}，数据无变化`)
      }
      // 重新加载详情
      await loadMovieDetail(true)
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '刷新失败'
    ElMessage.error(errorMsg)
  } finally {
    loadingRef.value = false
  }
}

// 刷新PT资源信息
const handleRefreshResources = async (silent: boolean = false) => {
  if (!movie.value) return

  const startTime = Date.now()

  // 设置 loading 状态（手动刷新和自动刷新都显示）
  refreshing.value = true

  // 显示开始刷新的提示
  if (!silent) {
    ElMessage.info(`正在刷新 ${ptResources.value.length} 个资源...`)
  } else {
    // 自动刷新时显示更轻量的提示
    ElMessage({
      message: `检测到资源信息已过期，正在后台自动刷新...`,
      type: 'info',
      duration: 2000,
      showClose: false
    })
  }

  try {
    const response = await api.movie.refreshMovieResources(movie.value.id)

    // 刷新成功后重新加载电影详情
    // 注意：传入 skipAutoRefresh=true，避免循环刷新
    const movieId = Number(route.params.id)
    const detailResponse = await api.movie.getMovieDetail(movieId)

    if (detailResponse?.data && detailResponse.data.id) {
      movie.value = detailResponse.data as any
      const resources = detailResponse.data.ptResources || []

      // 调试：检查返回的数据格式
      console.log('PT Resources from API:', resources)
      console.log('Is Array:', Array.isArray(resources))
      if (resources.length > 0) {
        console.log('First resource:', resources[0])
      }

      ptResources.value = resources
    }

    const result = response.data
    if (!result) {
      throw new Error('刷新响应数据格式错误')
    }

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)

    // 显示刷新结果
    if (silent) {
      // 自动刷新：显示简洁的成功消息
      if (result.failed > 0) {
        ElMessage.warning(`自动刷新完成：${result.success}/${result.total} 个成功`)
      } else {
        ElMessage.success({
          message: `自动刷新完成，已更新 ${result.success} 个资源`,
          duration: 2000
        })
      }
      console.log(`自动刷新：${result.success}/${result.total} 个资源成功，耗时 ${elapsed}s`)
    } else {
      // 手动刷新：显示详细消息
      if (result.failed > 0) {
        ElMessage.warning(
          `已刷新 ${result.success}/${result.total} 个资源，${result.failed} 个失败 (耗时 ${elapsed}s)`
        )
      } else {
        ElMessage.success(`已刷新 ${result.success} 个资源 (耗时 ${elapsed}s)`)
      }
    }
  } catch (error) {
    console.error('Failed to refresh resources:', error)
    if (!silent) {
      ElMessage.error('刷新资源信息失败')
    } else {
      ElMessage.error('自动刷新失败')
    }
  } finally {
    refreshing.value = false
  }
}

// 手动同步PT资源
const handleSyncPTResources = async () => {
  if (!movie.value) return

  syncing.value = true

  try {
    // 调用同步API（不指定站点，同步所有启用的站点）
    const response = await api.movie.syncMoviePTResources(movie.value.id)
    // 响应拦截器返回的 response 对象，后端数据在 response.data 中
    const responseData = response.data

    // 判断返回的是单个任务还是多个任务
    if (responseData.execution_id) {
      // 单个任务
      ElMessage.success(responseData.message || '同步任务已创建')
      // 显示任务进度弹窗
      currentTaskExecutionId.value = responseData.execution_id
      taskProgressVisible.value = true
      syncing.value = false
    } else if (responseData.execution_ids && responseData.execution_ids.length > 0) {
      // 多个任务
      ElMessage.success(responseData.message || `已创建 ${responseData.sites_count} 个同步任务`)
      // 轮询第一个任务的状态
      pollSyncTaskStatus(responseData.execution_ids)
    } else {
      throw new Error('未返回有效的任务ID')
    }
  } catch (error) {
    ElMessage.error('创建同步任务失败')
    syncing.value = false
  }
}

// 轮询同步任务状态
const pollSyncTaskStatus = async (executionIds: number[]) => {
  const poll = async () => {
    try {
      // 查询第一个任务的状态（简化逻辑）
      const taskRes = await api.task.getTaskExecution(executionIds[0])
      const taskData = taskRes.data?.data || taskRes.data

      if (taskData.status === 'completed') {
        // 任务完成，重新加载详情
        await loadMovieDetail(true)
        syncing.value = false
        ElMessage.success('资源同步完成，请查看关联的PT资源列表')
      } else if (taskData.status === 'failed') {
        // 任务失败
        syncing.value = false
        ElMessage.error('资源同步失败')
      } else if (taskData.status === 'running' || taskData.status === 'pending') {
        // 继续轮询
        setTimeout(poll, 3000)  // 3秒后继续轮询
      } else {
        // 其他状态
        syncing.value = false
      }
    } catch (error) {
      console.error('Failed to poll task status:', error)
      syncing.value = false
    }
  }
  await poll()
}

// 处理下载
const handleDownload = (resource: PTResource) => {
  selectedResource.value = resource
  downloadDialogVisible.value = true
}

// 下载成功回调
const handleDownloadSuccess = (executionId?: number) => {
  if (executionId) {
    // 显示任务进度弹窗
    currentTaskExecutionId.value = executionId
    taskProgressVisible.value = true
  } else {
    // 兼容旧版本（如果没有返回executionId）
    ElMessage.success('下载任务创建成功')
  }
}

// 任务完成回调
const handleTaskCompleted = async () => {
  // 可以在这里刷新电影详情或做其他操作
  ElMessage.success('下载任务已完成')
}

// 打开链接
const handleOpenLink = (url: string) => {
  window.open(url, '_blank')
}

// 打开编辑对话框
const handleOpenEditDialog = () => {
  if (!movie.value) return

  // 将电影数据填充到表单
  editForm.imdbId = movie.value.imdbId || null
  editForm.tmdbId = movie.value.tmdbId || null
  editForm.doubanId = movie.value.doubanId || null
  editForm.title = movie.value.title || ''
  editForm.originalTitle = movie.value.originalTitle || null
  editForm.year = movie.value.year || null
  editForm.runtime = movie.value.runtime || null
  editForm.certification = (movie.value as any).certification || null
  editForm.ratingDouban = movie.value.ratingDouban || null
  editForm.ratingTmdb = movie.value.ratingTmdb || null
  editForm.ratingImdb = movie.value.ratingImdb || null
  editForm.votesDouban = movie.value.votesDouban || null
  editForm.votesTmdb = movie.value.votesTmdb || null
  editForm.votesImdb = movie.value.votesImdb || null
  editForm.genres = movie.value.genres ? [...movie.value.genres] : []
  editForm.countries = (movie.value as any).countries ? [...(movie.value as any).countries] : []
  editForm.overview = movie.value.overview || null
  editForm.tagline = (movie.value as any).tagline || null

  editDialogVisible.value = true
}

// 保存电影信息
const handleSaveMovie = async () => {
  if (!movie.value) return

  saving.value = true
  try {
    // 只发送有值的字段
    const updateData: MovieUpdateData = {}

    // 外部ID - 发送所有值（包括 null，用于清除）
    if (editForm.imdbId !== movie.value.imdbId) {
      updateData.imdbId = editForm.imdbId || null
    }
    if (editForm.tmdbId !== movie.value.tmdbId) {
      updateData.tmdbId = editForm.tmdbId || null
    }
    if (editForm.doubanId !== movie.value.doubanId) {
      updateData.doubanId = editForm.doubanId || null
    }

    // 基本信息
    if (editForm.title && editForm.title !== movie.value.title) {
      updateData.title = editForm.title
    }
    if (editForm.originalTitle !== movie.value.originalTitle) {
      updateData.originalTitle = editForm.originalTitle || null
    }
    if (editForm.year !== movie.value.year) {
      updateData.year = editForm.year || null
    }
    if (editForm.runtime !== movie.value.runtime) {
      updateData.runtime = editForm.runtime || null
    }
    if (editForm.certification !== (movie.value as any).certification) {
      updateData.certification = editForm.certification || null
    }

    // 评分和投票数
    if (editForm.ratingDouban !== movie.value.ratingDouban) {
      updateData.ratingDouban = editForm.ratingDouban || null
    }
    if (editForm.votesDouban !== movie.value.votesDouban) {
      updateData.votesDouban = editForm.votesDouban || null
    }
    if (editForm.ratingTmdb !== movie.value.ratingTmdb) {
      updateData.ratingTmdb = editForm.ratingTmdb || null
    }
    if (editForm.votesTmdb !== movie.value.votesTmdb) {
      updateData.votesTmdb = editForm.votesTmdb || null
    }
    if (editForm.ratingImdb !== movie.value.ratingImdb) {
      updateData.ratingImdb = editForm.ratingImdb || null
    }
    if (editForm.votesImdb !== movie.value.votesImdb) {
      updateData.votesImdb = editForm.votesImdb || null
    }

    // 分类
    const currentGenres = movie.value.genres || []
    if (JSON.stringify(editForm.genres) !== JSON.stringify(currentGenres)) {
      updateData.genres = editForm.genres && editForm.genres.length > 0 ? editForm.genres : null
    }
    const currentCountries = (movie.value as any).countries || []
    if (JSON.stringify(editForm.countries) !== JSON.stringify(currentCountries)) {
      updateData.countries = editForm.countries && editForm.countries.length > 0 ? editForm.countries : null
    }

    // 内容
    if (editForm.overview !== movie.value.overview) {
      updateData.overview = editForm.overview || null
    }
    if (editForm.tagline !== (movie.value as any).tagline) {
      updateData.tagline = editForm.tagline || null
    }

    // 检查是否有修改
    if (Object.keys(updateData).length === 0) {
      ElMessage.info('没有需要保存的修改')
      editDialogVisible.value = false
      return
    }

    const response = await api.movie.updateMovie(movie.value.id, updateData)
    if (response.data) {
      ElMessage.success('电影信息更新成功')
      editDialogVisible.value = false
      // 重新加载电影详情
      await loadMovieDetail(true)
    }
  } catch (error: any) {
    console.error('Failed to update movie:', error)
    const errorMsg = error.response?.data?.detail || error.message || '更新失败'
    ElMessage.error(errorMsg)
  } finally {
    saving.value = false
  }
}

// 打开ID对应的站点链接
const openIdLink = (type: string, id: string | number) => {
  const urlMap: Record<string, string> = {
    imdb: `https://www.imdb.com/title/${id}`,
    tmdb_movie: `https://www.themoviedb.org/movie/${id}`,
    tmdb_tv: `https://www.themoviedb.org/tv/${id}`,
    tvdb: `https://thetvdb.com/dereferrer/series/${id}`,
    douban: `https://movie.douban.com/subject/${id}`
  }
  const url = urlMap[type]
  if (url) {
    window.open(url, '_blank')
  }
}

// 返回上一页
const handleBack = () => {
  // 获取当前所在的媒体库页签，默认是 'movies'
  const currentTab = route.query.tab || 'movies'
  router.push({
    path: '/resource-library',
    query: { tab: currentTab }
  })
}

// 格式化日期
const formatDate = (dateString: string) => {
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

// 格式化投票数
const formatVotes = (votes: number) => {
  if (!votes) return '0'
  if (votes >= 1000000) {
    return (votes / 1000000).toFixed(1) + 'M'
  }
  if (votes >= 1000) {
    return (votes / 1000).toFixed(1) + 'k'
  }
  return votes.toString()
}

onMounted(() => {
  loadMovieDetail()
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

.movie-detail-container {
  margin-top: 20px;
}

.movie-info-card {
  margin-bottom: 20px;
}

.movie-title {
  margin: 0 0 10px 0;
  font-size: 32px;
  font-weight: 700;
  color: var(--nf-text-primary);
}

.movie-original-title {
  margin: 0 0 20px 0;
  font-size: 20px;
  font-weight: 400;
  color: var(--nf-text-regular);
}

.movie-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 15px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  color: var(--nf-text-regular);
}

.meta-item.rating {
  color: #f7ba2a;
  font-weight: 600;
}

.movie-genres {
  margin-bottom: 15px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.movie-director,
.movie-cast {
  margin-bottom: 10px;
  font-size: 15px;
  color: var(--nf-text-regular);
}

.movie-overview {
  margin: 20px 0;
}

.movie-overview h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--nf-text-primary);
}

.movie-overview p {
  margin: 0;
  font-size: 15px;
  line-height: 1.8;
  color: var(--nf-text-regular);
  text-align: justify;
}

.movie-ids-row {
  margin-top: 15px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.movie-ids {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.id-link-tag {
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.id-link-tag:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

.id-icon {
  font-size: 12px;
  margin-right: 2px;
}

.id-group {
  display: inline-flex;
  align-items: stretch;
  transition: all 0.2s;
}

.id-group:hover {
  transform: translateY(-1px);
}

.id-group .el-tag {
  margin: 0;
  border-radius: 0;
}

.id-group .left-tag {
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
  border-right: 1px solid rgba(255, 255, 255, 0.3); /* 添加半透明分割线 */
  margin-right: -1px; /* 修正边框重叠 */
  z-index: 0;
}

.id-group .left-tag:hover {
  filter: brightness(1.1);
  z-index: 1; /* 确保 hover 时浮于上层 */
}

.id-group .right-tag {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  padding: 0 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-left: none; /* 移除右侧标签的左边框，避免双重边框 */
}

.id-group .right-tag:hover {
  filter: brightness(1.1);
}

.id-group .right-tag .el-icon.is-loading {
  animation: refresh-spin 1s linear infinite;
}

@keyframes refresh-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.pt-resources-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.resource-title {
  font-weight: 500;
  color: var(--nf-text-primary);
}

.resource-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--nf-text-secondary);
}

/* 海报与布局 */
.movie-header {
  display: flex;
  gap: 30px;
  align-items: flex-start;
}

.movie-poster-section {
  flex-shrink: 0;
}

.movie-poster {
  width: 260px;
  height: 370px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  display: block;
}

.image-slot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 260px;
  height: 370px;
  background-color: var(--bg-color-overlay);
  border-radius: 8px;
  font-size: 48px;
  color: var(--text-color-muted);
}

.movie-info-section {
  flex: 1;
  min-width: 0;
}

/* 评分卡片 */
.rating-cast-row {
  display: flex;
  align-items: stretch;
  gap: 0;
  margin-bottom: 12px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.rating-cards {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.rating-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  border-radius: 8px;
  background-color: var(--bg-color-overlay);
  border: 1px solid var(--border-color);
  min-width: 80px;
}

.rating-card.douban {
  border-color: rgba(0, 119, 34, 0.2);
  background-color: rgba(0, 119, 34, 0.05);
}

.rating-card.tmdb {
  border-color: rgba(1, 180, 228, 0.2);
  background-color: rgba(1, 180, 228, 0.05);
}

.rating-card.imdb {
  border-color: rgba(245, 197, 24, 0.2);
  background-color: rgba(245, 197, 24, 0.05);
}

.rating-source {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-bottom: 4px;
  font-weight: 500;
}

.rating-score {
  font-size: 20px;
  font-weight: bold;
  color: var(--text-color-primary);
  line-height: 1.2;
}

.douban .rating-score { color: #007722; }
.tmdb .rating-score { color: #01b4e4; }
.imdb .rating-score { color: #f5c518; }

html.dark .imdb .rating-score { color: #ffd700; }

.rating-votes {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-color-secondary);
}

/* 分隔符 */
.cast-separator {
  font-size: 22px;
  color: var(--text-color-secondary);
  opacity: 0.5;
  align-self: center;
  margin: 0 10px;
  flex-shrink: 0;
  user-select: none;
}

/* 演职人员列表 */
.cast-inline-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.cast-inline-actors {
  flex-shrink: 1;
  min-width: 0;
}

.cast-inline-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-color-secondary);
  writing-mode: vertical-lr;
  letter-spacing: 2px;
  flex-shrink: 0;
  user-select: none;
}

.cast-inline-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
}

.cast-inline-list::-webkit-scrollbar {
  display: none;
}

.cast-inline-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  width: 70px;
  flex-shrink: 0;
  transition: all 0.2s;
  position: relative;
}

.cast-inline-item:hover {
  transform: translateY(-2px);
}

.cast-inline-item:hover .cast-inline-name {
  color: var(--nf-primary, var(--el-color-primary));
}

/* 悬浮放大预览 */
.cast-inline-item:hover .cast-inline-avatar-wrap {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.cast-inline-item:hover .cast-inline-avatar-img {
  transform: scale(1.15);
}

/* 头像容器 */
.cast-inline-avatar-wrap {
  width: 64px;
  height: 85px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  margin-bottom: 4px;
  background-color: var(--bg-color-overlay);
  flex-shrink: 0;
  position: relative;
  transition: box-shadow 0.3s ease-out;
}

/* 骨架屏动画 */
.avatar-skeleton {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    var(--bg-color-overlay) 25%,
    rgba(255, 255, 255, 0.08) 50%,
    var(--bg-color-overlay) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  z-index: 0;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.cast-inline-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  position: relative;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.cast-inline-avatar-img.loaded {
  opacity: 1;
}

/* 隐藏骨架屏当图片加载完成 */
.cast-inline-avatar-img.loaded ~ .avatar-skeleton,
.cast-inline-avatar-fallback ~ .avatar-skeleton {
  display: none;
}

.cast-inline-avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--text-color-secondary);
  background-color: var(--bg-color-overlay);
  position: relative;
  z-index: 1;
}

.cast-inline-name {
  font-size: 11px;
  text-align: center;
  line-height: 1.3;
  color: var(--text-color-regular);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  width: 100%;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .movie-header {
    flex-direction: column;
  }

  /* 海报居中 */
  .movie-poster-section {
    align-self: center;
  }

  .movie-poster {
    width: 160px;
    max-width: 160px;
    height: 228px;
  }

  .image-slot {
    width: 160px;
    max-width: 160px;
    height: 228px;
  }

  /* 标题字号缩小 */
  .movie-title {
    font-size: 22px;
  }

  .movie-original-title {
    font-size: 15px;
    margin-bottom: 12px;
  }

  /* 评分+演职人员可折行 */
  .rating-cast-row {
    flex-wrap: wrap;
    gap: 10px;
  }

  .cast-separator {
    display: none;
  }

  /* IDs 行：上下排列，编辑按钮不挤压 */
  .movie-ids-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  /* 卡片头部可折行 */
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
