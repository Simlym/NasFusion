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
            <!-- 标题：始终显示 NFO 标题或目录名 -->
            <h1 class="title">
              {{ detail.nfo_data?.title || detail.directory.directory_name }}
              <span v-if="(detail.nfo_data?.year || detail.unified_resource?.year)" class="year">
                ({{ detail.nfo_data?.year || detail.unified_resource?.year }})
              </span>
            </h1>

            <!-- 关联状态行 -->
            <div class="resource-association">
              <template v-if="detail.unified_resource">
                <router-link
                  :to="`/${detail.unified_resource.media_type === 'movie' ? 'movies' : 'tv'}/${detail.unified_resource.id}`"
                  class="association-link"
                  @click.stop
                >
                  <el-tag type="success" effect="dark" size="small" class="association-tag">
                    已关联
                  </el-tag>
                  <span class="association-title">{{ detail.unified_resource.title }}</span>
                  <span v-if="detail.unified_resource.year" class="association-year">({{ detail.unified_resource.year }})</span>
                </router-link>
                <el-button size="small" text class="reassoc-btn" @click="showLinkDialog = true">
                  重新关联
                </el-button>
              </template>
              <template v-else>
                <el-tag type="warning" effect="dark" size="small">未关联</el-tag>
                <el-button size="small" type="warning" plain @click="showLinkDialog = true">
                  识别关联
                </el-button>
              </template>
            </div>

            <div class="meta-row">
              <!-- 评分：直接显示原始分值 -->
              <div v-if="detail.nfo_data?.rating" class="rating-badge">
                <span class="star-icon">★</span>
                <span class="rating-num">{{ Number(detail.nfo_data.rating).toFixed(1) }}</span>
                <span class="rating-max">/10</span>
              </div>

              <!-- 外部ID链接 -->
              <a
                v-if="detail.nfo_data?.imdb_id"
                :href="`https://www.imdb.com/title/${detail.nfo_data.imdb_id}`"
                target="_blank"
                class="ext-link"
                @click.stop
              >
                <el-tag size="small" type="warning" effect="dark" class="id-tag">
                  IMDb
                </el-tag>
              </a>
              <a
                v-if="detail.nfo_data?.tmdb_id"
                :href="`https://www.themoviedb.org/${detail.directory.media_type === 'tv' ? 'tv' : 'movie'}/${detail.nfo_data.tmdb_id}`"
                target="_blank"
                class="ext-link"
                @click.stop
              >
                <el-tag size="small" type="primary" effect="dark" class="id-tag">
                  TMDB
                </el-tag>
              </a>

              <span v-if="detail.nfo_data?.runtime" class="meta-item">{{ detail.nfo_data.runtime }} 分钟</span>
              <span v-if="detail.directory.season_number" class="meta-item">第 {{ detail.directory.season_number }} 季</span>
              <el-tag v-if="detail.directory.media_type" size="small" type="info" effect="dark" class="meta-tag">
                {{ detail.directory.media_type.toUpperCase() }}
              </el-tag>
            </div>

            <!-- 元数据状态 -->
            <div class="metadata-status">
              <el-tooltip content="NFO 文件" placement="top">
                <el-tag :type="detail.directory.has_nfo ? 'success' : 'danger'" size="small" effect="dark" class="status-tag">
                  NFO
                </el-tag>
              </el-tooltip>
              <el-tooltip content="海报图片" placement="top">
                <el-tag :type="detail.directory.has_poster ? 'success' : 'danger'" size="small" effect="dark" class="status-tag">
                  海报
                </el-tag>
              </el-tooltip>
              <el-tooltip content="背景图片" placement="top">
                <el-tag :type="detail.directory.has_backdrop ? 'success' : 'info'" size="small" effect="dark" class="status-tag">
                  背景
                </el-tag>
              </el-tooltip>

              <!-- 刮削按钮 -->
              <el-dropdown
                v-if="videoFiles.length > 0"
                @command="handleDirectoryAction"
                style="margin-left: 12px"
                trigger="click"
              >
                <el-button size="small" type="primary" plain :loading="batchScraping || batchGenerating">
                  刮削 <el-icon style="margin-left:4px"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="scrape-all">全部（图片+NFO）</el-dropdown-item>
                    <el-dropdown-item command="generate-nfo-all">仅 NFO</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
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

          <!-- 文件列表 Tab -->
          <el-tab-pane name="files">
            <template #label>
              <span>
                文件列表
                <el-badge
                  v-if="missingNfoCount > 0"
                  :value="missingNfoCount"
                  type="danger"
                  style="margin-left: 4px"
                />
              </span>
            </template>

            <div class="files-toolbar">
              <div class="files-summary">
                <span class="stat-item">
                  <span class="stat-value">{{ videoFiles.length }}</span>
                  <span class="stat-label">个视频</span>
                </span>
                <span class="stat-divider"></span>
                <span class="stat-item">
                  <span class="stat-label">NFO</span>
                  <span :class="['stat-value', missingNfoCount > 0 ? 'is-danger' : 'is-success']">
                    {{ videoFiles.length - missingNfoCount }}/{{ videoFiles.length }}
                  </span>
                </span>
                <span class="stat-divider"></span>
                <span class="stat-item">
                  <span class="stat-label">图片</span>
                  <span :class="['stat-value', missingPosterCount > 0 ? 'is-warning' : 'is-success']">
                    {{ videoFiles.length - missingPosterCount }}/{{ videoFiles.length }}
                  </span>
                </span>
                <span class="stat-divider"></span>
                <span class="stat-item">
                  <span class="stat-value">{{ formatFileSize(detail.statistics.total_size) }}</span>
                </span>
              </div>
            </div>

            <!-- 视频文件表格 -->
            <el-table :data="sortedVideoFiles" stripe style="width: 100%">
              <el-table-column v-if="isSeasonDirectory" label="集数" width="70" align="center">
                <template #default="{ row }">
                  <span class="ep-num">
                    {{ row.episode_number != null ? `E${String(row.episode_number).padStart(2, '0')}` : '-' }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="文件名" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                  <div>
                    <div class="ep-title" v-if="row.episode_title">{{ row.episode_title }}</div>
                    <el-text size="small" type="info" class="ep-filename">{{ row.file_name }}</el-text>
                  </div>
                </template>
              </el-table-column>

              <el-table-column prop="file_size" label="大小" width="90" align="center">
                <template #default="{ row }">
                  {{ formatFileSize(row.file_size) }}
                </template>
              </el-table-column>

              <el-table-column label="分辨率" width="90" align="center">
                <template #default="{ row }">
                  <el-tag
                    v-if="row.resolution"
                    :type="resolutionTagType(row.resolution)"
                    size="small"
                    effect="dark"
                    disable-transitions
                  >
                    {{ row.resolution }}
                  </el-tag>
                  <span v-else style="color: #909399">-</span>
                </template>
              </el-table-column>

              <el-table-column label="NFO" width="60" align="center">
                <template #default="{ row }">
                  <el-icon :color="row.has_nfo ? '#67c23a' : '#f56c6c'" :size="18">
                    <CircleCheck v-if="row.has_nfo" />
                    <CircleClose v-else />
                  </el-icon>
                </template>
              </el-table-column>

              <el-table-column label="图片" width="60" align="center">
                <template #default="{ row }">
                  <el-icon :color="row.has_poster ? '#67c23a' : '#f56c6c'" :size="18">
                    <CircleCheck v-if="row.has_poster" />
                    <CircleClose v-else />
                  </el-icon>
                </template>
              </el-table-column>

              <el-table-column label="字幕" width="60" align="center">
                <template #default="{ row }">
                  <el-tooltip
                    v-if="row.has_subtitle"
                    :content="row.subtitle_paths && row.subtitle_paths.length > 0 ? '外挂字幕' : '内嵌字幕'"
                    placement="top"
                  >
                    <el-icon :color="'#67c23a'" :size="18">
                      <CircleCheck />
                    </el-icon>
                  </el-tooltip>
                  <el-icon v-else :color="'#909399'" :size="18">
                    <Minus />
                  </el-icon>
                </template>
              </el-table-column>

              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :loading="scrapingIds.has(row.id)"
                    @click="handleScrapeFile(row.id)"
                  >
                    刮削
                  </el-button>
                  <el-button
                    link
                    type="info"
                    size="small"
                    :loading="generatingIds.has(row.id)"
                    @click="handleGenerateNFOFile(row.id)"
                  >
                    NFO
                  </el-button>
                  <el-button
                    v-if="row.jellyfin_web_url"
                    link
                    type="success"
                    size="small"
                    @click="openInJellyfin(row)"
                  >
                    播放
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 非视频文件（字幕、图片、NFO等） -->
            <div v-if="nonVideoFiles.length > 0" class="other-files-section">
              <el-divider content-position="left">
                <el-text size="small" type="info" @click="showOtherFiles = !showOtherFiles" style="cursor: pointer">
                  其他文件 ({{ nonVideoFiles.length }})
                  <el-icon style="margin-left: 4px; vertical-align: middle">
                    <ArrowDown v-if="!showOtherFiles" />
                    <ArrowUp v-else />
                  </el-icon>
                </el-text>
              </el-divider>
              <el-table v-if="showOtherFiles" :data="nonVideoFiles" stripe style="width: 100%" size="small">
                <el-table-column prop="file_name" label="文件名" min-width="300" show-overflow-tooltip />
                <el-table-column prop="file_size" label="大小" width="100">
                  <template #default="{ row }">
                    {{ formatFileSize(row.file_size) }}
                  </template>
                </el-table-column>
                <el-table-column prop="extension" label="类型" width="80" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="getFileTypeTag(row)" effect="plain">
                      {{ (row.extension || '').replace('.', '').toUpperCase() || '-' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>

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
               <el-descriptions-item label="IMDB ID">
                 <a v-if="detail.nfo_data?.imdb_id" :href="`https://www.imdb.com/title/${detail.nfo_data.imdb_id}`" target="_blank">
                   {{ detail.nfo_data.imdb_id }}
                 </a>
                 <span v-else>-</span>
               </el-descriptions-item>
               <el-descriptions-item label="TMDB ID">{{ detail.nfo_data?.tmdb_id || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
        </el-tabs>
      </div>

    </template>
    <el-empty v-else description="请选择一个目录查看详情" />

    <!-- 识别关联对话框 -->
    <el-dialog v-model="showLinkDialog" title="识别关联" width="700px" destroy-on-close @open="onLinkDialogOpen" class="link-dialog">
      <!-- 搜索区域 -->
      <div class="search-form-wrapper">
        <el-form :inline="true" size="default" @submit.prevent="handleSearch">
          <el-form-item label="名称">
            <el-input
              v-model="linkForm.search_keyword"
              placeholder="输入名称搜索"
              clearable
              style="width: 260px"
            />
          </el-form-item>
          <el-form-item label="类型">
            <el-radio-group v-model="linkForm.media_type">
              <el-radio value="tv">剧集</el-radio>
              <el-radio value="movie">电影</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="来源">
            <el-radio-group v-model="linkForm.search_source">
              <el-radio value="local">本地资源</el-radio>
              <el-radio value="tmdb">TMDB</el-radio>
              <el-radio value="douban">豆瓣</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="searching" @click="handleSearch">搜索</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 当前关联状态 -->
      <div v-if="detail?.directory.unified_resource_id" style="margin-bottom: 12px;">
        <el-text type="info" size="small">
          当前已关联: {{ detail.directory.unified_table_name }} #{{ detail.directory.unified_resource_id }}
          {{ detail.directory.series_name ? `(${detail.directory.series_name})` : '' }}
        </el-text>
      </div>

      <!-- 选中状态 -->
      <div v-if="selectedItem" class="selected-preview">
        <el-tag type="success" effect="dark" size="small" style="margin-right: 6px">
          {{ selectedItem.source === 'local' ? '本地资源' : selectedItem.source === 'tmdb' ? 'TMDB' : '豆瓣' }}
        </el-tag>
        <span>{{ selectedItem.title }}</span>
        <span v-if="selectedItem.year" style="color: var(--el-text-color-secondary); margin-left: 4px">({{ selectedItem.year }})</span>
        <el-button link type="danger" size="small" style="margin-left: 8px" @click="clearSelection">取消选择</el-button>
      </div>

      <!-- 搜索结果列表 -->
      <div v-loading="searching" class="search-results-container">
        <el-empty v-if="!searching && localResults.length === 0 && tmdbResults.length === 0 && doubanResults.length === 0 && searchPerformed" description="未找到匹配结果，请尝试修改关键词或切换搜索来源" />

        <template v-if="localResults.length > 0">
          <div class="result-section-title">
            <el-tag type="success" effect="plain" size="small">本地资源库</el-tag>
            <span class="result-section-hint">已存在的统一资源，可直接关联</span>
          </div>
          <div class="search-results-list">
            <div
              v-for="item in localResults"
              :key="'local-' + item.unified_table_name + '-' + item.id"
              class="search-result-card"
              :class="{ selected: isSelected(item) }"
              @click="selectItem(item)"
            >
              <el-image
                :src="item.poster_url || ''"
                fit="cover"
                class="result-poster"
                lazy
              >
                <template #error>
                  <div class="result-poster-placeholder">
                    <el-icon :size="24"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="result-info">
                <div class="result-title">{{ item.title }}</div>
                <div v-if="item.original_title && item.original_title !== item.title" class="result-original-title">{{ item.original_title }}</div>
                <div class="result-meta">
                  <span v-if="item.year">{{ item.year }}</span>
                  <span v-if="item.rating" class="result-rating">
                    <span class="star-icon">★</span> {{ Number(item.rating).toFixed(1) }}
                  </span>
                  <el-tag size="small" effect="plain" round>{{ item.unified_table_name === 'unified_movies' ? '电影' : '剧集' }}</el-tag>
                </div>
                <div v-if="item.genres?.length" class="result-genres">
                  <el-tag v-for="g in item.genres.slice(0, 4)" :key="g" size="small" effect="plain" round>{{ g }}</el-tag>
                </div>
              </div>
              <el-icon v-if="isSelected(item)" class="result-check" :size="24"><CircleCheck /></el-icon>
            </div>
          </div>
        </template>

        <template v-if="tmdbResults.length > 0">
          <div class="result-section-title" :style="{ marginTop: localResults.length > 0 ? '16px' : '0' }">
            <el-tag type="primary" effect="plain" size="small">TMDB 在线搜索</el-tag>
            <span class="result-section-hint">从TMDB获取并创建新资源</span>
          </div>
          <div class="search-results-list">
            <div
              v-for="item in tmdbResults"
              :key="'tmdb-' + item.tmdb_id"
              class="search-result-card"
              :class="{ selected: isSelected(item) }"
              @click="selectItem(item)"
            >
              <el-image
                :src="item.poster_url || ''"
                fit="cover"
                class="result-poster"
                lazy
              >
                <template #error>
                  <div class="result-poster-placeholder">
                    <el-icon :size="24"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="result-info">
                <div class="result-title">{{ item.title }}</div>
                <div v-if="item.original_title && item.original_title !== item.title" class="result-original-title">{{ item.original_title }}</div>
                <div class="result-meta">
                  <span v-if="item.year">{{ item.year }}</span>
                  <span v-if="item.rating_tmdb" class="result-rating">
                    <span class="star-icon">★</span> {{ Number(item.rating_tmdb).toFixed(1) }}
                  </span>
                  <el-tag size="small" type="info" effect="plain" round>TMDB</el-tag>
                </div>
                <div v-if="item.genres?.length" class="result-genres">
                  <el-tag v-for="g in item.genres.slice(0, 4)" :key="g" size="small" effect="plain" round>{{ g }}</el-tag>
                </div>
                <div v-if="item.overview" class="result-overview">{{ item.overview }}</div>
              </div>
              <el-icon v-if="isSelected(item)" class="result-check" :size="24"><CircleCheck /></el-icon>
            </div>
          </div>
        </template>

        <template v-if="doubanResults.length > 0">
          <div class="result-section-title" :style="{ marginTop: localResults.length > 0 || tmdbResults.length > 0 ? '16px' : '0' }">
            <el-tag type="warning" effect="plain" size="small">豆瓣搜索</el-tag>
            <span class="result-section-hint">从豆瓣获取并创建新资源</span>
          </div>
          <div class="search-results-list">
            <div
              v-for="item in doubanResults"
              :key="'douban-' + item.douban_id"
              class="search-result-card"
              :class="{ selected: isSelected(item) }"
              @click="selectItem(item)"
            >
              <el-image
                :src="item.poster_url || ''"
                fit="cover"
                class="result-poster"
                lazy
              >
                <template #error>
                  <div class="result-poster-placeholder">
                    <el-icon :size="24"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="result-info">
                <div class="result-title">{{ item.title }}</div>
                <div class="result-meta">
                  <span v-if="item.year">{{ item.year }}</span>
                  <span v-if="item.rating_douban" class="result-rating">
                    <span class="star-icon">★</span> {{ Number(item.rating_douban).toFixed(1) }}
                  </span>
                  <el-tag size="small" type="warning" effect="plain" round>豆瓣</el-tag>
                </div>
                <div v-if="item.overview" class="result-overview">{{ item.overview }}</div>
              </div>
              <el-icon v-if="isSelected(item)" class="result-check" :size="24"><CircleCheck /></el-icon>
            </div>
          </div>
        </template>
      </div>

      <template #footer>
        <el-button @click="showLinkDialog = false">取消</el-button>
        <el-button type="primary" :loading="linking" :disabled="!selectedItem" @click="handleLinkDirectory">确认关联</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Picture,
  CircleCheck,
  CircleClose,
  Minus,
  ArrowDown,
  ArrowUp
} from '@element-plus/icons-vue'
import { getDirectoryDetail, linkDirectoryToResource, searchTMDBForDirectory, searchDoubanForDirectory, type DirectoryDetailResponse } from '@/api/mediaDirectory'
import type { TMDBCandidate } from '@/types/media'
import { getMovieList } from '@/api/modules/movie'
import { getTVList } from '@/api/modules/tv'
import { scrapeMediaFile, generateNFO, batchScrapeMediaFiles } from '@/api/modules/media'
import { getProxiedImageUrl } from '@/utils'

interface Props {
  directoryId: number | null
}

const props = defineProps<Props>()
const loading = ref(false)
const detail = ref<DirectoryDetailResponse | null>(null)
const activeTab = ref('files')

// 刮削状态
const scrapingIds = ref<Set<number>>(new Set())
const generatingIds = ref<Set<number>>(new Set())
const batchScraping = ref(false)
const batchGenerating = ref(false)

const defaultPoster = 'https://via.placeholder.com/300x450?text=No+Poster'
const showOtherFiles = ref(false)

// 识别关联对话框
const showLinkDialog = ref(false)
const linking = ref(false)
const searching = ref(false)
const searchPerformed = ref(false)
const localResultsRaw = ref<any[]>([])
const tmdbResultsRaw = ref<TMDBCandidate[]>([])
const doubanResultsRaw = ref<any[]>([])
const search_keyword = ref('')

// 统一的选中项类型
interface SelectedItem {
  source: 'local' | 'tmdb' | 'douban'
  id?: number
  tmdb_id?: number
  douban_id?: string
  title: string
  original_title?: string
  year?: number
  poster_url?: string
  rating?: number
  genres?: string[]
  overview?: string
  unified_table_name?: string
  unified_resource_id?: number
  media_type?: string
}
const selectedItem = ref<SelectedItem | null>(null)
const linkForm = reactive({
  search_keyword: '' as string,
  media_type: 'tv' as string,
  search_source: 'local' as 'local' | 'tmdb' | 'douban',
})

// 是否是季度目录（用于显示剧集Tab）
const isSeasonDirectory = computed(() =>
  detail.value?.directory.season_number != null
)

// 视频文件列表（排除字幕、图片等）
const videoFiles = computed(() => {
  if (!detail.value) return []
  return detail.value.files.filter((f: any) => {
    if (f.file_type === 'video') return true
    const ext = (f.extension || '').toLowerCase().replace(/^\./, '')
      || (f.file_name?.split('.').pop() || '').toLowerCase()
    return ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'ts', 'flv', 'm2ts', 'rmvb', 'iso'].includes(ext)
  })
})

// 按集数排序的视频文件（剧集按集数，电影按文件名）
const sortedVideoFiles = computed(() => {
  return [...videoFiles.value].sort((a: any, b: any) => {
    if (isSeasonDirectory.value) {
      const ea = a.episode_number ?? 9999
      const eb = b.episode_number ?? 9999
      return ea - eb
    }
    return (a.file_name || '').localeCompare(b.file_name || '')
  })
})

// 非视频文件（字幕、图片、NFO等）
const nonVideoFiles = computed(() => {
  if (!detail.value) return []
  const videoSet = new Set(videoFiles.value.map((f: any) => f.id))
  return detail.value.files.filter((f: any) => !videoSet.has(f.id))
})

// 缺少NFO的集数
const missingNfoCount = computed(() =>
  videoFiles.value.filter((f: any) => !f.has_nfo).length
)

// 缺少图片的集数
const missingPosterCount = computed(() =>
  videoFiles.value.filter((f: any) => !f.has_poster).length
)

// Hero 背景样式
const heroStyle = computed(() => {
  if (detail.value?.directory.backdrop_path) {
    const proxiedUrl = getProxiedImageUrl(detail.value.directory.backdrop_path)
    return { '--backdrop-url': `url("${proxiedUrl}")` }
  }
  return { backgroundColor: 'var(--nf-bg-container, #221e30)' }
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

      // 默认显示文件列表
      activeTab.value = 'files'
    }
  } catch (error) {
    ElMessage.error('加载目录详情失败')
  } finally {
    loading.value = false
  }
}

const refresh = () => loadDetail()

// ===== 刮削操作 =====

async function handleScrapeFile(fileId: number) {
  scrapingIds.value.add(fileId)
  try {
    const res = await scrapeMediaFile(fileId, undefined, true)
    if (res.data.success) {
      ElMessage.success('刮削成功')
      await loadDetail()
    } else {
      ElMessage.error(res.data.errors?.[0] || '刮削失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '刮削失败')
  } finally {
    scrapingIds.value.delete(fileId)
  }
}

async function handleGenerateNFOFile(fileId: number) {
  generatingIds.value.add(fileId)
  try {
    const res = await generateNFO(fileId, undefined, true)
    if (res.data.success) {
      ElMessage.success(`NFO 生成成功`)
      await loadDetail()
    } else {
      ElMessage.error(res.data.error || 'NFO 生成失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'NFO 生成失败')
  } finally {
    generatingIds.value.delete(fileId)
  }
}

async function handleBatchScrapeEpisodes() {
  if (!videoFiles.value.length) return
  const ids = videoFiles.value.map((f: any) => f.id)
  try {
    await ElMessageBox.confirm(
      `确定要刮削全部 ${ids.length} 集文件吗？将覆盖已有的图片和NFO`,
      '批量刮削',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  batchScraping.value = true
  try {
    const res = await batchScrapeMediaFiles({ file_ids: ids })
    ElMessage.success(`批量刮削完成：成功 ${res.data.success_count}，失败 ${res.data.failed_count}`)
    await loadDetail()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '批量刮削失败')
  } finally {
    batchScraping.value = false
  }
}

async function handleBatchGenerateNFO() {
  if (!videoFiles.value.length) return
  const ids = videoFiles.value.map((f: any) => f.id)
  batchGenerating.value = true
  const results = { success: 0, failed: 0 }
  try {
    for (const id of ids) {
      try {
        const res = await generateNFO(id, undefined, true)
        if (res.data.success) results.success++
        else results.failed++
      } catch {
        results.failed++
      }
    }
    ElMessage.success(`NFO生成完成：成功 ${results.success}，失败 ${results.failed}`)
    await loadDetail()
  } finally {
    batchGenerating.value = false
  }
}

async function handleDirectoryAction(command: string) {
  if (command === 'scrape-all') {
    await handleBatchScrapeEpisodes()
  } else if (command === 'generate-nfo-all') {
    await handleBatchGenerateNFO()
  }
}

// ===== 识别关联 =====

// 统一的搜索结果：本地 + TMDB
const localResults = computed(() => localResultsRaw.value)
const tmdbResults = computed(() => tmdbResultsRaw.value)
const doubanResults = computed(() => doubanResultsRaw.value)

function isSelected(item: any): boolean {
  if (!selectedItem.value) return false
  if (item.source === 'local' || item.unified_table_name) {
    return selectedItem.value.source === 'local'
      && selectedItem.value.unified_table_name === item.unified_table_name
      && selectedItem.value.unified_resource_id === item.id
  }
  if (item.source === 'douban') {
    return selectedItem.value.source === 'douban' && selectedItem.value.douban_id === item.douban_id
  }
  return selectedItem.value.source === 'tmdb' && selectedItem.value.tmdb_id === item.tmdb_id
}

function selectItem(item: any) {
  if (item.source === 'local' || item.unified_table_name) {
    selectedItem.value = {
      source: 'local',
      id: item.id,
      title: item.title,
      original_title: item.original_title || item.originalTitle,
      year: item.year,
      poster_url: item.poster_url || item.posterUrl,
      rating: item.rating || item.ratingTmdb,
      genres: item.genres,
      unified_table_name: item.unified_table_name,
      unified_resource_id: item.id,
    }
  } else if (item.source === 'douban') {
    selectedItem.value = {
      source: 'douban',
      douban_id: item.douban_id,
      title: item.title,
      year: item.year,
      poster_url: item.poster_url,
      rating: item.rating_douban,
      overview: item.overview,
      media_type: linkForm.media_type,
    }
  } else {
    selectedItem.value = {
      source: 'tmdb',
      tmdb_id: item.tmdb_id,
      title: item.title,
      original_title: item.original_title,
      year: item.year,
      poster_url: item.poster_url,
      rating: item.rating_tmdb,
      genres: item.genres,
      overview: item.overview,
    }
  }
}

function clearSelection() {
  selectedItem.value = null
}

function onLinkDialogOpen() {
  const nfoTitle = detail.value?.nfo_data?.title
  const dirName = detail.value?.directory.directory_name || ''
  linkForm.search_keyword = nfoTitle || dirName
  // 根据目录的 media_type 或已关联的表名自动设置类型
  const dirMediaType = detail.value?.directory.media_type
  const linkedTable = detail.value?.directory.unified_table_name
  if (dirMediaType === 'movie' || dirMediaType === 'adult') {
    linkForm.media_type = 'movie'
  } else if (dirMediaType === 'tv' || dirMediaType === 'episode') {
    linkForm.media_type = 'tv'
  } else if (linkedTable === 'unified_movies') {
    linkForm.media_type = 'movie'
  } else if (linkedTable === 'unified_tv_series') {
    linkForm.media_type = 'tv'
  }
  selectedItem.value = null
  localResultsRaw.value = []
  tmdbResultsRaw.value = []
  doubanResultsRaw.value = []
  searchPerformed.value = false
  linkForm.search_source = 'local'
}

async function handleSearch() {
  if (!linkForm.search_keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  searching.value = true
  searchPerformed.value = true
  selectedItem.value = null

  const keyword = linkForm.search_keyword.trim()
  const mediaType = linkForm.media_type
  const source = linkForm.search_source

  // 清空对应来源的结果
  if (source === 'local') {
    localResultsRaw.value = []
  } else if (source === 'tmdb') {
    tmdbResultsRaw.value = []
  } else if (source === 'douban') {
    doubanResultsRaw.value = []
  }

  try {
    if (source === 'local') {
      const res = mediaType === 'movie'
        ? await getMovieList({ page: 1, pageSize: 10, search: keyword })
        : await getTVList({ page: 1, pageSize: 10, search: keyword })

      if (res?.data) {
        const items = res.data.items || []
        const tableName = mediaType === 'movie' ? 'unified_movies' : 'unified_tv_series'
        localResultsRaw.value = items.map((item: any) => ({
          ...item,
          source: 'local',
          unified_table_name: tableName,
          poster_url: item.posterUrl || item.poster_url || item.localPosterUrl || '',
          original_title: item.originalTitle || item.original_title || '',
          rating: item.ratingTmdb || item.rating_tmdb || item.rating || null,
          genres: Array.isArray(item.genres) ? item.genres : [],
          overview: item.overview || item.plot || '',
        }))

        if (localResultsRaw.value.length === 1) {
          selectItem(localResultsRaw.value[0])
        }
      }
    } else if (source === 'tmdb') {
      const res = await searchTMDBForDirectory({
        title: keyword,
        media_type: mediaType,
      })
      if (res?.data) {
        tmdbResultsRaw.value = (res.data.results || []).map((item: any) => ({
          ...item,
          source: 'tmdb',
        }))
      }
    } else if (source === 'douban') {
      const res = await searchDoubanForDirectory({
        title: keyword,
        media_type: mediaType,
      })
      if (res?.data) {
        doubanResultsRaw.value = (res.data.results || []).map((item: any) => ({
          ...item,
          source: 'douban',
        }))
      }
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '搜索失败')
  } finally {
    searching.value = false
  }
}

async function handleLinkDirectory() {
  if (!detail.value || !props.directoryId) return
  if (!selectedItem.value) {
    ElMessage.warning('请选择一个匹配结果')
    return
  }
  linking.value = true
  try {
    let res: any
    if (selectedItem.value.source === 'local') {
      // 直接关联本地资源
      res = await linkDirectoryToResource(props.directoryId, {
        unified_table_name: selectedItem.value.unified_table_name,
        unified_resource_id: selectedItem.value.unified_resource_id,
        media_type: linkForm.media_type,
      })
    } else if (selectedItem.value.source === 'douban') {
      // 通过豆瓣ID关联
      res = await linkDirectoryToResource(props.directoryId, {
        douban_id: selectedItem.value.douban_id,
        media_type: linkForm.media_type,
      })
    } else {
      // 通过TMDB ID关联
      res = await linkDirectoryToResource(props.directoryId, {
        tmdb_id: selectedItem.value.tmdb_id,
        media_type: linkForm.media_type,
      })
    }
    if (res.data.success) {
      ElMessage.success(res.data.message || '关联成功')
      showLinkDialog.value = false
      await loadDetail()
    } else {
      ElMessage.error('关联失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '关联失败')
  } finally {
    linking.value = false
  }
}

// ===== 工具函数 =====

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

const formatTime = (timeStr: string) => new Date(timeStr).toLocaleString()

const getFileTypeTag = (row: any): string => {
  const ext = (row.extension || '').replace('.', '').toLowerCase()
  if (['nfo', 'xml'].includes(ext)) return 'warning'
  if (['srt', 'ass', 'ssa', 'sub', 'vtt'].includes(ext)) return 'success'
  if (['jpg', 'jpeg', 'png', 'webp', 'bmp'].includes(ext)) return 'primary'
  return 'info'
}

const resolutionTagType = (resolution: string): string => {
  const r = resolution.toLowerCase()
  if (r === '2160p' || r === '4k') return 'danger'
  if (r === '1080p') return 'warning'
  if (r === '720p') return 'success'
  return 'info'
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
  height: 420px;
  color: #fff;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-size: cover;
  background-position: center top;
  background-repeat: no-repeat;
  background-image: var(--backdrop-url, none);
  filter: blur(8px);
  transform: scale(1.1);
  z-index: 0;
}

.hero-overlay {
  position: absolute;
  inset: 0;
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
  align-items: flex-end;
}

.poster-wrapper {
  flex-shrink: 0;
  width: 200px;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border: 4px solid rgba(255,255,255,0.1);
  background: #222;
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

.info-wrapper {
  flex: 1;
  padding-bottom: 20px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.8);
}

.title {
  font-size: 30px;
  font-weight: 700;
  margin: 0 0 10px 0;
  line-height: 1.2;

  .year {
    font-weight: 400;
    font-size: 22px;
    opacity: 0.8;
    margin-left: 10px;
  }
}

/* 关联状态行 */
.resource-association {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .association-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    color: #fff;
    transition: opacity 0.2s;
    cursor: pointer;

    &:hover {
      opacity: 0.85;

      .association-title {
        text-decoration: underline;
        text-underline-offset: 3px;
      }
    }
  }

  .association-tag {
    flex-shrink: 0;
  }

  .association-title {
    font-size: 14px;
    font-weight: 500;
  }

  .association-year {
    font-size: 13px;
    opacity: 0.7;
  }

  .reassoc-btn {
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
    padding: 2px 6px;
    height: auto;

    &:hover {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

/* 评分徽章 */
.rating-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  background: rgba(255, 153, 0, 0.2);
  border: 1px solid rgba(255, 153, 0, 0.5);
  border-radius: 6px;
  padding: 2px 10px;

  .star-icon {
    font-size: 14px;
    color: #ff9900;
  }

  .rating-num {
    font-size: 20px;
    font-weight: 700;
    color: #ff9900;
    line-height: 1;
  }

  .rating-max {
    font-size: 12px;
    color: rgba(255, 153, 0, 0.7);
  }
}

.ext-link {
  text-decoration: none;
  .id-tag {
    cursor: pointer;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.meta-item {
  font-size: 14px;
  opacity: 0.9;
}

.meta-tag {
  backdrop-filter: blur(4px);
}

/* 元数据状态行 */
.metadata-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  .status-tag {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.genres-row {
  margin-bottom: 12px;

  .genre-tag {
    margin-right: 8px;
    background-color: rgba(255,255,255,0.2) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #fff !important;
  }
}

.plot {
  font-size: 14px;
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

/* 文件列表 Tab */
.files-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding: 10px 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);

  .files-summary {
    display: flex;
    align-items: center;
    gap: 0;
    font-size: 13px;
  }

  .stat-item {
    display: inline-flex;
    align-items: baseline;
    gap: 4px;
    padding: 0 12px;
  }

  .stat-label {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  .stat-value {
    font-weight: 600;
    font-size: 14px;
    color: var(--el-text-color-primary);
    font-variant-numeric: tabular-nums;

    &.is-success { color: var(--el-color-success); }
    &.is-warning { color: var(--el-color-warning); }
    &.is-danger { color: var(--el-color-danger); }
  }

  .stat-divider {
    width: 1px;
    height: 16px;
    background: var(--el-border-color-light);
    flex-shrink: 0;
  }

}

.other-files-section {
  margin-top: 16px;
}

.ep-num {
  font-family: monospace;
  font-weight: 600;
  font-size: 13px;
  color: var(--el-color-primary);
}

.ep-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  line-height: 1.4;
}

.ep-filename {
  font-size: 11px;
  display: block;
  margin-top: 2px;
}

/* 演职人员 */
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


:deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
}

/* 选中预览 */
.selected-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-color-success);
  border-radius: var(--nf-radius-sm, 6px);
  margin-bottom: 12px;
  font-size: 14px;
}

/* 搜索表单区域 */
.search-form-wrapper {
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--nf-radius-base, 8px);
  margin-bottom: 16px;
  border: 1px solid var(--el-border-color-lighter);
}

/* 搜索结果区域标题 */
.result-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  .result-section-hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

/* 搜索结果 */
.search-results-container {
  min-height: 120px;
  max-height: 450px;
  overflow-y: auto;
}

.search-results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-result-card {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: var(--nf-radius-base, 8px);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  background: var(--el-bg-color);
  box-shadow: var(--nf-shadow-xs, 0 1px 2px rgba(0, 0, 0, 0.04));

  &:hover {
    border-color: var(--el-color-primary-light-5);
    background: var(--el-fill-color-lighter);
    box-shadow: var(--nf-shadow-sm, 0 2px 4px rgba(0, 0, 0, 0.06));
  }

  &.selected {
    border-color: var(--el-color-success);
    background: var(--el-fill-color-lighter);
    box-shadow: 0 0 0 1px var(--el-color-success-light-5);
  }
}

.result-poster {
  flex-shrink: 0;
  width: 60px;
  height: 90px;
  border-radius: var(--nf-radius-xs, 4px);
  overflow: hidden;
  background: var(--el-fill-color);
}

.result-poster-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color);
}

.result-info {
  flex: 1;
  min-width: 0;
}

.result-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  margin-bottom: 2px;
  color: var(--el-text-color-primary);
}

.result-original-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;

  .result-rating {
    .star-icon {
      color: var(--el-color-warning, #ff9900);
      font-size: 12px;
    }
  }
}

.result-genres {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.result-overview {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-check {
  position: absolute;
  top: 10px;
  right: 10px;
  color: var(--el-color-success);
}
</style>
