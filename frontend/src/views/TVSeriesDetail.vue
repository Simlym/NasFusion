<template>
  <div class="page-container">
    <el-page-header @back="handleBack">
      <template #content>
        <span class="page-title">剧集详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" class="tv-detail-container">
      <!-- 剧集信息卡片 -->
      <el-card v-if="tvSeries" class="tv-info-card">
        <!-- 上层：海报 + 基本信息 -->
        <div class="tv-header">
          <div class="tv-poster-section">
            <el-image
              v-if="tvSeries.posterUrl"
              :src="getProxiedImageUrl(tvSeries.posterUrl)"
              fit="cover"
              class="tv-poster"
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

          <div class="tv-info-section">
            <h1 class="tv-title">{{ tvSeries.title }}</h1>
            <h2 v-if="tvSeries.originalTitle" class="tv-original-title">
              {{ tvSeries.originalTitle }}
            </h2>

            <div class="tv-meta-row">
              <div v-if="tvSeries.year" class="meta-item">
                <el-icon><Calendar /></el-icon>
                <span>{{ tvSeries.year }}</span>
                <span v-if="tvSeries.status" class="status-tag" :class="getStatusClass(tvSeries.status)">
                  {{ getStatusText(tvSeries.status) }}
                </span>
              </div>
              <div v-if="tvSeries.numberOfSeasons || tvSeries.numberOfEpisodes" class="meta-item">
                <el-icon><VideoCamera /></el-icon>
                <span v-if="tvSeries.numberOfSeasons">{{ tvSeries.numberOfSeasons }} 季</span>
                <span v-if="tvSeries.numberOfEpisodes"> · {{ tvSeries.numberOfEpisodes }} 集</span>
              </div>
              <div v-if="tvSeries.firstAirDate || tvSeries.lastAirDate" class="meta-item">
                <span v-if="tvSeries.firstAirDate">{{ formatDateOnly(tvSeries.firstAirDate) }}</span>
                <span v-if="tvSeries.lastAirDate"> 至 {{ formatDateOnly(tvSeries.lastAirDate) }}</span>
              </div>
            </div>

            <!-- 评分 + 导演/主演 合并行 -->
            <div class="rating-cast-row">
              <!-- 评分区 -->
              <div v-if="tvSeries.ratingDouban || tvSeries.ratingTmdb || tvSeries.ratingImdb" class="rating-cards">
                <div v-if="tvSeries.ratingDouban" class="rating-card douban">
                  <div class="rating-source">豆瓣</div>
                  <div class="rating-score">{{ tvSeries.ratingDouban.toFixed(1) }}</div>
                  <div v-if="tvSeries.votesDouban" class="rating-votes">
                    <el-icon><User /></el-icon>
                    {{ formatVotes(tvSeries.votesDouban) }} 评价
                  </div>
                </div>
                <div v-if="tvSeries.ratingTmdb" class="rating-card tmdb">
                  <div class="rating-source">TMDB</div>
                  <div class="rating-score">{{ tvSeries.ratingTmdb.toFixed(1) }}</div>
                  <div v-if="tvSeries.votesTmdb" class="rating-votes">
                    <el-icon><User /></el-icon>
                    {{ formatVotes(tvSeries.votesTmdb) }} 评价
                  </div>
                </div>
                <div v-if="tvSeries.ratingImdb" class="rating-card imdb">
                  <div class="rating-source">IMDB</div>
                  <div class="rating-score">{{ tvSeries.ratingImdb.toFixed(1) }}</div>
                  <div v-if="tvSeries.votesImdb" class="rating-votes">
                    <el-icon><User /></el-icon>
                    {{ formatVotes(tvSeries.votesImdb) }} 评价
                  </div>
                </div>
              </div>

              <!-- 分隔符：评分与人物 -->
              <span v-if="(tvSeries.ratingDouban || tvSeries.ratingTmdb || tvSeries.ratingImdb) && (tvSeries.directors?.length || tvSeries.actors?.length)" class="cast-separator">·</span>

              <!-- 导演区 -->
              <div v-if="tvSeries.directors && tvSeries.directors.length" class="cast-inline-group">
                <span class="cast-inline-label">导演</span>
                <div class="cast-inline-list">
                  <div v-for="director in tvSeries.directors" :key="director.id" class="cast-inline-item" @click="goToPerson(director.id)">
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
              <span v-if="tvSeries.directors?.length && tvSeries.actors?.length" class="cast-separator">·</span>

              <!-- 主演区 -->
              <div v-if="tvSeries.actors && tvSeries.actors.length" class="cast-inline-group cast-inline-actors">
                <span class="cast-inline-label">主演</span>
                <div class="cast-inline-list">
                  <div v-for="actor in tvSeries.actors.slice(0, 8)" :key="actor.id" class="cast-inline-item" @click="goToPerson(actor.id)">
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

            <div v-if="tvSeries.genres && tvSeries.genres.length" class="tv-genres">
              <el-tag v-for="genre in tvSeries.genres" :key="genre" size="small" effect="plain">
                {{ genre }}
              </el-tag>
            </div>

            <div v-if="tvSeries.overview" class="tv-overview">
              <h3>剧情简介</h3>
              <p>{{ tvSeries.overview }}</p>
            </div>

            <div v-if="tvSeries.networks && tvSeries.networks.length" class="tv-networks">
              <strong>播出网络：</strong>{{ tvSeries.networks.join('、') }}
            </div>

            <!-- ID标签 + 操作按钮 -->
            <div class="tv-ids-row">
              <div class="tv-ids">
                <el-tag v-if="tvSeries.imdbId" size="small" class="id-link-tag" @click="openIdLink('imdb', tvSeries.imdbId)">
                  <el-icon class="id-icon"><Link /></el-icon> IMDB: {{ tvSeries.imdbId }}
                </el-tag>
                <div v-if="tvSeries.tmdbId" class="id-group">
                  <el-tag size="small" type="success" class="id-link-tag left-tag" @click="openIdLink('tmdb_tv', tvSeries.tmdbId)">
                    <el-icon class="id-icon"><Link /></el-icon> TMDB: {{ tvSeries.tmdbId }}
                  </el-tag>
                  <el-tag size="small" type="success" class="right-tag" :class="{ 'is-loading': refreshingTmdb }" @click="handleRefreshMetadata('tmdb')">
                    <el-icon :class="{ 'is-loading': refreshingTmdb }"><Refresh /></el-icon>
                  </el-tag>
                </div>
                <el-tag v-if="tvSeries.tvdbId" size="small" type="info" class="id-link-tag" @click="openIdLink('tvdb', tvSeries.tvdbId)">
                  <el-icon class="id-icon"><Link /></el-icon> TVDB: {{ tvSeries.tvdbId }}
                </el-tag>
                <div v-if="tvSeries.doubanId" class="id-group">
                  <el-tag size="small" type="warning" class="id-link-tag left-tag" @click="openIdLink('douban', tvSeries.doubanId)">
                    <el-icon class="id-icon"><Link /></el-icon> 豆瓣: {{ tvSeries.doubanId }}
                  </el-tag>
                  <el-tag size="small" type="warning" class="right-tag" :class="{ 'is-loading': refreshingDouban }" @click="handleRefreshMetadata('douban')">
                    <el-icon :class="{ 'is-loading': refreshingDouban }"><Refresh /></el-icon>
                  </el-tag>
                </div>
              </div>
              <div class="tv-header-actions">
                <el-button size="small" :icon="Edit" @click="handleOpenEditDialog">编辑</el-button>
                <el-button type="primary" size="small" :icon="Bell" @click="handleSubscribe">订阅剧集</el-button>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- PT资源列表卡片 -->
      <el-card v-if="tvSeries" class="pt-resources-card">
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
      :unified-table-name="'unified_tv_series'"
      :unified-resource-id="tvSeries?.id"
      @success="handleDownloadSuccess"
    />

    <!-- 任务进度弹窗 -->
    <TaskProgressDialog
      v-model="taskProgressVisible"
      :task-execution-id="currentTaskExecutionId"
      @completed="handleTaskCompleted"
    />

    <!-- 订阅对话框 -->
    <SubscriptionDialog
      v-model:visible="subscriptionDialogVisible"
      :media-type="'tv'"
      :unified-tv-id="tvSeries?.id"
      :title="tvSeries?.title || ''"
      :original-title="tvSeries?.originalTitle"
      :year="tvSeries?.year"
      :poster-url="tvSeries?.posterUrl"
      :tmdb-id="tvSeries?.tmdbId"
      :imdb-id="tvSeries?.imdbId"
      :douban-id="tvSeries?.doubanId"
      :number-of-seasons="tvSeries?.numberOfSeasons"
      :number-of-episodes="tvSeries?.numberOfEpisodes"
      @success="handleSubscriptionSuccess"
    />

    <!-- 编辑电视剧信息对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑剧集信息"
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
            <el-form-item label="TVDB ID" prop="tvdbId">
              <el-input-number
                v-model="editForm.tvdbId"
                :min="1"
                :controls="false"
                placeholder="如: 123456"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="豆瓣 ID" prop="doubanId">
              <el-input v-model="editForm.doubanId" placeholder="如: 12345678" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="标题" prop="title">
          <el-input v-model="editForm.title" placeholder="剧集标题" />
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
            <el-form-item label="状态" prop="status">
              <el-select v-model="editForm.status" placeholder="选择状态" style="width: 100%">
                <el-option label="连载中" value="Returning Series" />
                <el-option label="已完结" value="Ended" />
                <el-option label="已取消" value="Canceled" />
                <el-option label="制作中" value="In Production" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="季数" prop="numberOfSeasons">
              <el-input-number
                v-model="editForm.numberOfSeasons"
                :min="1"
                :controls="false"
                placeholder="季数"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="集数" prop="numberOfEpisodes">
              <el-input-number
                v-model="editForm.numberOfEpisodes"
                :min="1"
                :controls="false"
                placeholder="总集数"
                style="width: 100%"
              />
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
        <el-form-item label="播出网络" prop="networks">
          <el-select
            v-model="editForm.networks"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入播出网络"
            style="width: 100%"
          >
            <el-option
              v-for="network in commonNetworks"
              :key="network"
              :label="network"
              :value="network"
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
            placeholder="剧集简介"
          />
        </el-form-item>
        <el-form-item label="宣传语" prop="tagline">
          <el-input v-model="editForm.tagline" placeholder="剧集宣传语" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveTVSeries">
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
import { Picture, Calendar, VideoCamera, Star, Bell, Refresh, Link, User, Edit } from '@element-plus/icons-vue'
import api from '@/api'
import type { UnifiedTVWithPTResources, PTResource } from '@/types'
import type { TVUpdateData } from '@/api/modules/tv'
import DownloadDialog from '@/components/download/DownloadDialog.vue'
import TaskProgressDialog from '@/components/TaskProgressDialog.vue'
import SubscriptionDialog from '@/components/subscription/SubscriptionDialog.vue'
import { getProxiedImageUrl } from '@/utils'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const refreshing = ref(false)
const syncing = ref(false)
const refreshingTmdb = ref(false)
const refreshingDouban = ref(false)
const tvSeries = ref<UnifiedTVWithPTResources | null>(null)
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

// 订阅相关
const subscriptionDialogVisible = ref(false)

// 编辑相关
const editDialogVisible = ref(false)
const saving = ref(false)
const editFormRef = ref()
const editForm = reactive<TVUpdateData>({
  imdbId: null,
  tmdbId: null,
  tvdbId: null,
  doubanId: null,
  title: '',
  originalTitle: null,
  year: null,
  status: null,
  numberOfSeasons: null,
  numberOfEpisodes: null,
  ratingDouban: null,
  ratingTmdb: null,
  ratingImdb: null,
  votesDouban: null,
  votesTmdb: null,
  votesImdb: null,
  genres: [],
  countries: [],
  networks: [],
  overview: null,
  tagline: null
})

// 常用类型选项
const commonGenres = [
  '剧情', '喜剧', '动作', '爱情', '科幻', '悬疑', '惊悚', '恐怖',
  '犯罪', '动画', '冒险', '奇幻', '战争', '传记', '历史', '音乐',
  '歌舞', '家庭', '儿童', '纪录片', '真人秀', '脱口秀', '综艺'
]

// 常用国家/地区选项
const commonCountries = [
  '中国大陆', '中国香港', '中国台湾', '美国', '日本', '韩国',
  '英国', '法国', '德国', '意大利', '西班牙', '印度', '泰国',
  '加拿大', '澳大利亚', '俄罗斯', '巴西', '墨西哥'
]

// 常用播出网络选项
const commonNetworks = [
  'Netflix', 'HBO', 'Amazon Prime Video', 'Disney+', 'Apple TV+',
  'Hulu', 'Paramount+', 'Peacock', 'AMC', 'FX', 'Showtime', 'Starz',
  'BBC', 'ITV', 'Channel 4', 'Sky', 'NHK', 'TVB', 'KBS', 'SBS', 'MBC',
  '央视', '湖南卫视', '浙江卫视', '东方卫视', '北京卫视', '江苏卫视',
  '爱奇艺', '优酷', '腾讯视频', '芒果TV', 'B站'
]

// 刷新元数据（从 TMDB 或豆瓣）
const handleRefreshMetadata = async (source: string) => {
  if (!tvSeries.value) return

  const loadingRef = source === 'tmdb' ? refreshingTmdb : refreshingDouban
  loadingRef.value = true

  try {
    const response = await api.tv.refreshTVMetadata(tvSeries.value.id, source)
    const result = response.data
    if (result) {
      const fieldCount = result.updatedFields?.length || 0
      if (fieldCount > 0) {
        ElMessage.success(`${result.message}，更新了 ${fieldCount} 个字段`)
      } else {
        ElMessage.info(`${result.message}，数据无变化`)
      }
      // 重新加载详情
      await loadTVDetail(true)
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '刷新失败'
    ElMessage.error(errorMsg)
  } finally {
    loadingRef.value = false
  }
}

// 刷新PT资源信息（异步任务）
const handleRefreshResources = async (silent: boolean = false, onlyCurrentPage: boolean = false) => {
  if (!tvSeries.value) return

  // 设置 loading 状态
  refreshing.value = true

  // 确定刷新范围
  const resourceIds = onlyCurrentPage
    ? ptResources.value.map(r => r.id) // 只刷新当前页的资源
    : undefined // 刷新全部

  const scope = onlyCurrentPage ? '当前页资源' : '所有资源'

  // 显示开始刷新的提示
  if (!silent) {
    ElMessage.info(`正在创建刷新任务（${scope}）...`)
  } else {
    ElMessage({
      message: `检测到资源信息已过期，正在后台自动刷新...`,
      type: 'info',
      duration: 2000,
      showClose: false
    })
  }

  try {
    // 创建刷新任务
    const response = await api.tv.refreshTVResources(tvSeries.value.id, resourceIds)
    // 响应拦截器返回的 response 对象，后端数据在 response.data 中
    const executionId = response.data?.execution_id

    if (!executionId) {
      throw new Error('刷新任务创建失败')
    }

    // 显示任务进度弹窗（手动刷新）或轮询任务状态（自动刷新）
    if (!silent) {
      // 手动刷新：显示任务进度弹窗
      currentTaskExecutionId.value = executionId
      taskProgressVisible.value = true
      refreshing.value = false
    } else {
      // 自动刷新：后台轮询任务状态
      pollTaskStatus(executionId, true)
    }
  } catch (error) {
    console.error('Failed to create refresh task:', error)
    if (!silent) {
      ElMessage.error('创建刷新任务失败')
    } else {
      ElMessage.error('自动刷新失败')
    }
    refreshing.value = false
  }
}

// 轮询任务状态（用于自动刷新）
const pollTaskStatus = async (executionId: number, isSilent: boolean) => {
  const poll = async () => {
    try {
      const taskRes = await api.task.getTaskExecution(executionId)
      const taskData = taskRes.data?.data || taskRes.data

      if (taskData.status === 'completed') {
        // 任务完成，重新加载详情
        await loadTVDetail(true)
        refreshing.value = false

        if (isSilent) {
          ElMessage.success({
            message: '资源刷新完成',
            duration: 2000
          })
        } else {
          ElMessage.success('资源刷新完成')
        }
      } else if (taskData.status === 'failed') {
        // 任务失败
        refreshing.value = false
        ElMessage.error('资源刷新失败')
      } else if (taskData.status === 'running' || taskData.status === 'pending') {
        // 继续轮询
        setTimeout(poll, 2000)
      } else {
        // 其他状态
        refreshing.value = false
      }
    } catch (error) {
      console.error('Failed to poll task status:', error)
      refreshing.value = false
    }
  }
  await poll()
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

    // 在后台异步执行刷新（只刷新当前页，避免请求过多）
    handleRefreshResources(true, true).catch((error) => {
      console.warn('自动刷新失败:', error)
    })

    // 立即返回，不等待刷新完成
  } else {
    // console.log('所有资源都在有效期内，无需刷新')
  }
}

// 加载剧集详情
const loadTVDetail = async (skipAutoRefresh = false) => {
  loading.value = true
  try {
    const tvId = Number(route.params.id)
    const response = await api.tv.getTVDetail(tvId, {
      ptPage: ptCurrentPage.value,
      ptPageSize: ptPageSize.value
    })

    // 响应拦截器返回完整的 response 对象，需要访问 response.data
    if (response?.data && response.data.id) {
      tvSeries.value = response.data as any
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

      // ⚠️ 已禁用自动刷新：避免触发站点频率限制导致封禁
      // 检查是否需要自动刷新资源（可选跳过，避免循环刷新）
      // if (!skipAutoRefresh) {
      //   await checkAndAutoRefresh()
      // }
    } else {
      console.error('Invalid response format:', response)
      ElMessage.error('返回数据格式错误')
    }
  } catch (error) {
    console.error('Failed to load TV detail:', error)
    ElMessage.error('加载剧集详情失败')
  } finally {
    loading.value = false
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
  loadTVDetail(true) // 跳过自动刷新
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  ptPageSize.value = size
  ptCurrentPage.value = 1 // 重置到第一页
  loadTVDetail(true) // 跳过自动刷新
}

// 跳转到人员详情
const goToPerson = (personId: number) => {
  if (!personId || isNaN(personId)) {
    ElMessage.warning('该人员尚未关联，无法跳转')
    return
  }
  router.push(`/person/${personId}`)
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
  // 可以在这里刷新剧集详情或做其他操作
  ElMessage.success('下载任务已完成')
}

// 处理订阅
const handleSubscribe = () => {
  subscriptionDialogVisible.value = true
}

// 订阅成功回调
const handleSubscriptionSuccess = () => {
  ElMessage.success('订阅创建成功')
}

// 打开编辑对话框
const handleOpenEditDialog = () => {
  if (!tvSeries.value) return

  // 将电视剧数据填充到表单
  editForm.imdbId = tvSeries.value.imdbId || null
  editForm.tmdbId = tvSeries.value.tmdbId || null
  editForm.tvdbId = tvSeries.value.tvdbId || null
  editForm.doubanId = tvSeries.value.doubanId || null
  editForm.title = tvSeries.value.title || ''
  editForm.originalTitle = tvSeries.value.originalTitle || null
  editForm.year = tvSeries.value.year || null
  editForm.status = tvSeries.value.status || null
  editForm.numberOfSeasons = tvSeries.value.numberOfSeasons || null
  editForm.numberOfEpisodes = tvSeries.value.numberOfEpisodes || null
  editForm.ratingDouban = tvSeries.value.ratingDouban || null
  editForm.ratingTmdb = tvSeries.value.ratingTmdb || null
  editForm.ratingImdb = tvSeries.value.ratingImdb || null
  editForm.votesDouban = tvSeries.value.votesDouban || null
  editForm.votesTmdb = tvSeries.value.votesTmdb || null
  editForm.votesImdb = tvSeries.value.votesImdb || null
  editForm.genres = tvSeries.value.genres ? [...tvSeries.value.genres] : []
  editForm.countries = (tvSeries.value as any).countries ? [...(tvSeries.value as any).countries] : []
  editForm.networks = tvSeries.value.networks ? [...tvSeries.value.networks] : []
  editForm.overview = tvSeries.value.overview || null
  editForm.tagline = (tvSeries.value as any).tagline || null

  editDialogVisible.value = true
}

// 保存电视剧信息
const handleSaveTVSeries = async () => {
  if (!tvSeries.value) return

  saving.value = true
  try {
    // 只发送有值的字段
    const updateData: TVUpdateData = {}

    // 外部ID - 发送所有值（包括 null，用于清除）
    if (editForm.imdbId !== tvSeries.value.imdbId) {
      updateData.imdbId = editForm.imdbId || null
    }
    if (editForm.tmdbId !== tvSeries.value.tmdbId) {
      updateData.tmdbId = editForm.tmdbId || null
    }
    if (editForm.tvdbId !== tvSeries.value.tvdbId) {
      updateData.tvdbId = editForm.tvdbId || null
    }
    if (editForm.doubanId !== tvSeries.value.doubanId) {
      updateData.doubanId = editForm.doubanId || null
    }

    // 基本信息
    if (editForm.title && editForm.title !== tvSeries.value.title) {
      updateData.title = editForm.title
    }
    if (editForm.originalTitle !== tvSeries.value.originalTitle) {
      updateData.originalTitle = editForm.originalTitle || null
    }
    if (editForm.year !== tvSeries.value.year) {
      updateData.year = editForm.year || null
    }
    if (editForm.status !== tvSeries.value.status) {
      updateData.status = editForm.status || null
    }
    if (editForm.numberOfSeasons !== tvSeries.value.numberOfSeasons) {
      updateData.numberOfSeasons = editForm.numberOfSeasons || null
    }
    if (editForm.numberOfEpisodes !== tvSeries.value.numberOfEpisodes) {
      updateData.numberOfEpisodes = editForm.numberOfEpisodes || null
    }

    // 评分和投票数
    if (editForm.ratingDouban !== tvSeries.value.ratingDouban) {
      updateData.ratingDouban = editForm.ratingDouban || null
    }
    if (editForm.votesDouban !== tvSeries.value.votesDouban) {
      updateData.votesDouban = editForm.votesDouban || null
    }
    if (editForm.ratingTmdb !== tvSeries.value.ratingTmdb) {
      updateData.ratingTmdb = editForm.ratingTmdb || null
    }
    if (editForm.votesTmdb !== tvSeries.value.votesTmdb) {
      updateData.votesTmdb = editForm.votesTmdb || null
    }
    if (editForm.ratingImdb !== tvSeries.value.ratingImdb) {
      updateData.ratingImdb = editForm.ratingImdb || null
    }
    if (editForm.votesImdb !== tvSeries.value.votesImdb) {
      updateData.votesImdb = editForm.votesImdb || null
    }

    // 分类
    const currentGenres = tvSeries.value.genres || []
    if (JSON.stringify(editForm.genres) !== JSON.stringify(currentGenres)) {
      updateData.genres = editForm.genres && editForm.genres.length > 0 ? editForm.genres : null
    }
    const currentCountries = (tvSeries.value as any).countries || []
    if (JSON.stringify(editForm.countries) !== JSON.stringify(currentCountries)) {
      updateData.countries = editForm.countries && editForm.countries.length > 0 ? editForm.countries : null
    }
    const currentNetworks = tvSeries.value.networks || []
    if (JSON.stringify(editForm.networks) !== JSON.stringify(currentNetworks)) {
      updateData.networks = editForm.networks && editForm.networks.length > 0 ? editForm.networks : null
    }

    // 内容
    if (editForm.overview !== tvSeries.value.overview) {
      updateData.overview = editForm.overview || null
    }
    if (editForm.tagline !== (tvSeries.value as any).tagline) {
      updateData.tagline = editForm.tagline || null
    }

    // 检查是否有修改
    if (Object.keys(updateData).length === 0) {
      ElMessage.info('没有需要保存的修改')
      editDialogVisible.value = false
      return
    }

    const response = await api.tv.updateTVSeries(tvSeries.value.id, updateData)
    if (response.data) {
      ElMessage.success('剧集信息更新成功')
      editDialogVisible.value = false
      // 重新加载剧集详情
      await loadTVDetail(true)
    }
  } catch (error: any) {
    console.error('Failed to update TV series:', error)
    const errorMsg = error.response?.data?.detail || error.message || '更新失败'
    ElMessage.error(errorMsg)
  } finally {
    saving.value = false
  }
}

// 手动同步PT资源
const handleSyncPTResources = async () => {
  if (!tvSeries.value) return

  syncing.value = true

  try {
    // 调用同步API（不指定站点，同步所有启用的站点）
    const response = await api.tv.syncTVPTResources(tvSeries.value.id)
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
        await loadTVDetail(true)
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

// 打开链接
const handleOpenLink = (url: string) => {
  window.open(url, '_blank')
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
  // 获取当前所在的媒体库页签，默认是 'tv'
  const currentTab = route.query.tab || 'tv'
  router.push({
    path: '/resource-library',
    query: { tab: currentTab }
  })
}

// 获取状态样式类
const getStatusClass = (status: string) => {
  if (status === 'Returning Series' || status === 'In Production') {
    return 'status-ongoing'
  } else if (status === 'Ended') {
    return 'status-ended'
  } else if (status === 'Canceled') {
    return 'status-canceled'
  }
  return ''
}

// 获取状态显示文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'Returning Series': '连载中',
    'Ended': '已完结',
    'Canceled': '已取消',
    'In Production': '制作中'
  }
  return statusMap[status] || status
}

// 格式化日期时间
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

// 格式化日期（仅日期）
const formatDateOnly = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
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
  loadTVDetail()
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

.tv-detail-container {
  margin-top: 20px;
}

.tv-info-card {
  margin-bottom: 20px;
}

.tv-header {
  display: flex;
  gap: 24px;
}

.tv-poster-section {
  flex-shrink: 0;
}

.tv-poster {
  width: 260px;
  height: 370px;
  border-radius: 8px;
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

.tv-info-section {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.tv-title {
  margin: 0 0 4px 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--text-color-primary);
  line-height: 1.3;
}

.tv-original-title {
  margin: 0 0 10px 0;
  font-size: 16px;
  font-weight: 400;
  color: var(--text-color-secondary);
}

.tv-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--text-color-regular);
}

.meta-item.rating {
  color: #f7ba2a;
  font-weight: 600;
}

/* 评分 + 演职人员 合并行 */
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
  justify-content: center;
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

.cast-inline-item:hover .cast-inline-avatar-wrap {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.cast-inline-item:hover .cast-inline-avatar-img {
  transform: scale(1.15);
}

/* 悬浮弹出大图 */
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

.rating-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  border-radius: 8px;
  min-width: 85px;
  background: var(--bg-color-overlay);
  border: 1px solid var(--border-color);
  box-shadow: var(--box-shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
}

.rating-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--box-shadow-md);
}

.rating-card.douban {
  background: linear-gradient(135deg, rgba(45, 122, 45, 0.1), rgba(26, 92, 26, 0.05));
  border-color: rgba(45, 122, 45, 0.2);
}

.rating-card.tmdb {
  background: linear-gradient(135deg, rgba(1, 180, 228, 0.1), rgba(13, 37, 63, 0.05));
  border-color: rgba(1, 180, 228, 0.2);
}

.rating-card.imdb {
  background: linear-gradient(135deg, rgba(245, 197, 24, 0.1), rgba(0, 0, 0, 0.05));
  border-color: rgba(245, 197, 24, 0.2);
}

.rating-source {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-color-secondary);
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rating-score {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.rating-card.douban .rating-score {
  color: #2d7a2d;
}

html.dark .rating-card.douban .rating-score {
  color: #4ea84e;
}

.rating-card.tmdb .rating-score {
  color: #01b4e4;
}

.rating-card.imdb .rating-score {
  color: #f5c518;
}

.rating-votes {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--text-color-secondary);
  margin-top: 2px;
}

.rating-votes .el-icon {
  font-size: 11px;
}

.vote-count {
  color: var(--text-color-secondary);
  font-weight: 400;
  font-size: 13px;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: white;
  margin-left: 8px;
}

.status-ongoing {
  background-color: var(--success-color);
}

.status-ended {
  background-color: var(--text-color-secondary);
}

.status-canceled {
  background-color: var(--danger-color);
}

.tv-genres {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tv-airdate,
.tv-creators,
.tv-cast,
.tv-networks {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-color-regular);
}

.tv-ids-row {
  margin-top: auto;
  padding-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.tv-header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.tv-ids {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
  border-right: 1px solid rgba(255, 255, 255, 0.3);
  margin-right: -1px;
  z-index: 0;
}

.id-group .left-tag:hover {
  filter: brightness(1.1);
  z-index: 1;
}

.id-group .right-tag {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  padding: 0 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-left: none;
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

.tv-overview {
  margin-bottom: 10px;
}

.tv-overview h3 {
  margin: 0 0 6px 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color-primary);
}

.tv-overview p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-color-regular);
  text-align: justify;
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
  color: var(--text-color-primary);
}

.resource-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .tv-header {
    flex-direction: column;
  }

  /* 海报居中 */
  .tv-poster-section {
    align-self: center;
  }

  .tv-poster {
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
  .tv-title {
    font-size: 22px;
  }

  .tv-original-title {
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

  /* IDs 行：上下排列 */
  .tv-ids-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .tv-header-actions {
    flex-wrap: wrap;
    gap: 6px;
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
