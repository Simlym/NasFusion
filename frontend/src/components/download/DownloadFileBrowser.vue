<template>
  <div class="download-file-browser">
    <!-- 下载目录操作栏 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <!-- PC 筛选栏 -->
      <el-row v-if="!isMobile" :gutter="16" align="middle">
        <el-col :span="5">
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 100%" @change="loadFiles">
            <el-option label="全部" value="" />
            <el-option label="已发现" value="discovered" />
            <el-option label="已识别" value="identified" />
            <el-option label="整理中" value="organizing" />
            <el-option label="刮削中" value="scraping" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.organized" placeholder="是否整理" clearable style="width: 100%" @change="loadFiles">
            <el-option label="全部" :value="undefined" />
            <el-option label="未整理" :value="false" />
            <el-option label="已整理" :value="true" />
          </el-select>
        </el-col>
        <el-col :span="14" style="text-align: right">
          <el-button-group>
            <el-button type="success" :icon="Search" :disabled="selectedIds.length === 0" @click="handleBatchIdentify">
              批量识别 ({{ selectedIds.length }})
            </el-button>
            <el-button type="warning" :icon="FolderOpened" :disabled="selectedIds.length === 0" @click="handleBatchOrganize">
              批量整理 ({{ selectedIds.length }})
            </el-button>
            <el-button type="primary" :icon="Refresh" @click="loadFiles">刷新</el-button>
            <el-button type="info" :icon="Folder" :loading="scanning" @click="scanDownloads">扫描目录</el-button>
          </el-button-group>
        </el-col>
      </el-row>

      <!-- Mobile 筛选栏 -->
      <div v-else class="mobile-toolbar">
        <div class="mobile-filters">
          <el-select v-model="filters.status" placeholder="状态筛选" clearable style="flex: 1" @change="loadFiles">
            <el-option label="全部状态" value="" />
            <el-option label="已发现" value="discovered" />
            <el-option label="已识别" value="identified" />
            <el-option label="整理中" value="organizing" />
            <el-option label="刮削中" value="scraping" />
          </el-select>
          <el-select v-model="filters.organized" placeholder="整理状态" clearable style="flex: 1" @change="loadFiles">
            <el-option label="全部" :value="undefined" />
            <el-option label="未整理" :value="false" />
            <el-option label="已整理" :value="true" />
          </el-select>
        </div>
        <div class="mobile-actions">
          <el-button type="primary" :icon="Refresh" size="small" @click="loadFiles">刷新</el-button>
          <el-button type="info" :icon="Folder" size="small" :loading="scanning" @click="scanDownloads">扫描</el-button>
          <el-button
            v-if="selectedIds.length > 0"
            type="success"
            :icon="Search"
            size="small"
            @click="handleBatchIdentify"
          >识别({{ selectedIds.length }})</el-button>
          <el-button
            v-if="selectedIds.length > 0"
            type="warning"
            :icon="FolderOpened"
            size="small"
            @click="handleBatchOrganize"
          >整理({{ selectedIds.length }})</el-button>
        </div>
      </div>
    </el-card>

    <!-- 媒体文件列表 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>下载目录文件 ({{ pagination.total }})</span>
        </div>
      </template>

      <!-- PC: 表格视图 -->
      <el-table
        v-if="!isMobile"
        v-loading="loading"
        :data="files"
        height="600"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="文件名" min-width="200">
          <template #default="{ row }">
            <div>
              <div>{{ row.file_name }}</div>
              <div v-if="row.sub_title" class="file-subtitle">{{ row.sub_title }}</div>
              <el-text size="small" type="info">{{ row.directory }}</el-text>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="120">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="识别状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.unified_resource_id" type="success">已识别</el-tag>
            <el-tag v-else type="info">未识别</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否整理" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.organized" type="success">已整理</el-tag>
            <el-tag v-else type="info">未整理</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="整理目录" min-width="200">
          <template #default="{ row }">
            <div v-if="row.organized && row.organized_path">
              <el-text size="small">{{ row.organized_path }}</el-text>
              <el-tag v-if="row.organize_mode" size="small" type="warning" style="margin-left: 8px">
                {{ getOrganizeModeLabel(row.organize_mode) }}
              </el-tag>
            </div>
            <el-text v-else size="small" type="info">-</el-text>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-dropdown trigger="click" @command="(cmd: string) => handleAction(cmd, row.id)">
              <el-button size="small" type="primary">
                操作<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="identify" :icon="Search">识别</el-dropdown-item>
                  <el-dropdown-item command="organize" :icon="FolderOpened">整理</el-dropdown-item>
                  <template v-if="row.organized">
                    <el-dropdown-item divided command="scrape" :icon="Download">重新刮削图片+NFO</el-dropdown-item>
                    <el-dropdown-item command="generate-nfo" :icon="Document">重新生成NFO</el-dropdown-item>
                  </template>
                  <el-dropdown-item divided command="delete" :icon="Delete" class="delete-item">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- Mobile: 卡片视图 -->
      <div v-else v-loading="loading" class="file-card-list">
        <div v-if="files.length === 0 && !loading" class="file-empty">暂无文件记录</div>
        <div v-for="row in files" :key="row.id" class="file-card">
          <div class="file-card-header">
            <div class="file-card-name">{{ row.file_name }}</div>
            <el-dropdown trigger="click" @command="(cmd: string) => handleAction(cmd, row.id)">
              <el-button size="small" type="primary" plain circle>
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="identify" :icon="Search">识别</el-dropdown-item>
                  <el-dropdown-item command="organize" :icon="FolderOpened">整理</el-dropdown-item>
                  <template v-if="row.organized">
                    <el-dropdown-item divided command="scrape" :icon="Download">重新刮削图片+NFO</el-dropdown-item>
                    <el-dropdown-item command="generate-nfo" :icon="Document">重新生成NFO</el-dropdown-item>
                  </template>
                  <el-dropdown-item divided command="delete" :icon="Delete" class="delete-item">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div v-if="row.sub_title" class="file-card-subtitle">{{ row.sub_title }}</div>
          <div class="file-card-path">{{ row.directory }}</div>
          <div class="file-card-meta">
            <span class="file-card-size">{{ formatFileSize(row.file_size) }}</span>
            <div class="file-card-badges">
              <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
              <el-tag v-if="row.unified_resource_id" type="success" size="small">已识别</el-tag>
              <el-tag v-else type="info" size="small">未识别</el-tag>
              <el-tag v-if="row.organized" type="success" size="small">已整理</el-tag>
              <el-tag v-else type="info" size="small">未整理</el-tag>
            </div>
          </div>
          <div v-if="row.organized && row.organized_path" class="file-card-organized-path">
            <el-tag v-if="row.organize_mode" size="small" type="warning">{{ getOrganizeModeLabel(row.organize_mode) }}</el-tag>
            <span class="organized-path-text">{{ row.organized_path }}</span>
          </div>
        </div>
      </div>

      <!-- PC 分页 -->
      <el-pagination
        v-if="!isMobile"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="loadFiles"
        @current-change="loadFiles"
      />
      <!-- Mobile 分页 -->
      <el-pagination
        v-else
        v-model:current-page="pagination.page"
        :total="pagination.total"
        :page-size="pagination.size"
        layout="prev, pager, next"
        small
        style="margin-top: 16px; justify-content: center"
        @current-change="loadFiles"
      />
    </el-card>

    <!-- 整理对话框 -->
    <el-dialog
      v-model="organizeDialog.visible"
      title="整理文件"
      width="600px"
      :close-on-click-modal="!organizeDialog.loading"
      :close-on-press-escape="!organizeDialog.loading"
      v-loading="organizeDialog.loading"
      element-loading-text="正在整理文件，请稍候..."
    >
      <el-form label-width="100px">
        <el-form-item label="选择配置">
          <el-select v-model="organizeDialog.configId" placeholder="选择整理配置" style="width: 100%">
            <el-option
              v-for="config in configs"
              :key="config.id"
              :label="config.name"
              :value="config.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="目标媒体目录">
          <el-select v-model="organizeDialog.storageMountId" placeholder="选择目标媒体目录" style="width: 100%">
            <el-option
              v-for="mount in storageMounts"
              :key="mount.id"
              :label="`${mount.name} (${mount.container_path})`"
              :value="mount.id"
            />
          </el-select>
        </el-form-item>

        <!-- 电视剧季集输入（仅单文件整理时显示，且非电影类型） -->
        <template v-if="organizeDialog.fileIds.length === 1 && organizeDialog.unifiedTableName !== 'unified_movies' && (organizeDialog.mediaType === 'tv' || organizeDialog.mediaType === 'anime')">
          <el-form-item label="季数">
            <el-input-number
              v-model="organizeDialog.seasonNumber"
              :min="1"
              :max="99"
              placeholder="请输入季数"
              style="width: 200px"
            />
            <el-text size="small" type="info" style="margin-left: 10px">
              {{ organizeDialog.seasonNumber ? `第 ${organizeDialog.seasonNumber} 季` : '未识别到季数' }}
            </el-text>
          </el-form-item>
          <el-form-item label="集数">
            <el-input-number
              v-model="organizeDialog.episodeNumber"
              :min="1"
              :max="999"
              placeholder="请输入集数"
              style="width: 200px"
            />
            <el-text size="small" type="info" style="margin-left: 10px">
              {{ organizeDialog.episodeNumber ? `第 ${organizeDialog.episodeNumber} 集` : '未识别到集数' }}
            </el-text>
          </el-form-item>
        </template>

        <!-- 批量整理提示 -->
        <el-alert
          v-if="organizeDialog.fileIds.length > 1"
          type="info"
          :closable="false"
          style="margin-bottom: 15px"
        >
          <template #title>
            批量整理 {{ organizeDialog.fileIds.length }} 个文件，将使用每个文件已识别的季集信息
          </template>
        </el-alert>

        <el-form-item label="强制整理">
          <el-switch v-model="organizeDialog.force" />
          <el-text size="small" type="info" style="margin-left: 10px">
            启用后忽略已整理状态，重新整理文件
          </el-text>
        </el-form-item>

        <el-form-item label="模拟运行">
          <el-switch v-model="organizeDialog.dryRun" />
          <el-text size="small" type="info" style="margin-left: 10px">
            启用后仅预览结果，不实际移动文件
          </el-text>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="organizeDialog.visible = false" :disabled="organizeDialog.loading">取消</el-button>
        <el-button type="primary" @click="confirmOrganize" :loading="organizeDialog.loading" :disabled="organizeDialog.loading">
          {{ organizeDialog.loading ? '整理中...' : '确定' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 识别对话框 -->
    <el-dialog v-model="identifyDialog.visible" title="识别媒体文件" width="900px">
      <div v-loading="identifyDialog.loading">
        <!-- 文件名解析信息 -->
        <el-card v-if="identifyDialog.parsedInfo" style="margin-bottom: 20px">
          <template #header>
            <span>文件名解析结果</span>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="标题">{{
              identifyDialog.parsedInfo.title || '-'
            }}</el-descriptions-item>
            <el-descriptions-item label="年份">{{
              identifyDialog.parsedInfo.year || '-'
            }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{
              identifyDialog.parsedInfo.type || '-'
            }}</el-descriptions-item>
            <el-descriptions-item label="季">{{
              identifyDialog.parsedInfo.season || '-'
            }}</el-descriptions-item>
            <el-descriptions-item label="集">{{
              identifyDialog.parsedInfo.episode || '-'
            }}</el-descriptions-item>
            <el-descriptions-item label="分辨率">{{
              identifyDialog.parsedInfo.resolution || '-'
            }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 手动搜索 -->
        <el-card style="margin-bottom: 20px">
          <template #header>
            <span>手动搜索</span>
          </template>
          <el-form :inline="true">
            <el-form-item label="标题">
              <el-input v-model="manualSearch.title" placeholder="输入标题" style="width: 200px" />
            </el-form-item>
            <el-form-item label="年份">
              <el-input-number
                v-model="manualSearch.year"
                :min="1900"
                :max="2030"
                style="width: 120px"
              />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="manualSearch.media_type" style="width: 120px">
                <el-option label="电影" value="movie" />
                <el-option label="电视剧" value="tv" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源">
              <el-radio-group v-model="manualSearch.search_source">
                <el-radio value="tmdb">TMDB</el-radio>
                <el-radio value="douban">豆瓣</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="manualSearch.loading" @click="handleManualSearch"
                >搜索</el-button
              >
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 候选列表 -->
        <el-card>
          <template #header>
            <span>搜索结果 ({{ identifyDialog.candidates.length }})</span>
          </template>
          <div
            v-if="identifyDialog.candidates.length === 0"
            style="text-align: center; padding: 20px"
          >
            <el-empty description="暂无搜索结果，请尝试手动搜索" />
          </div>
          <div v-else class="candidates-list">
            <div
              v-for="(candidate, idx) in identifyDialog.candidates"
              :key="(candidate as any)._source === 'douban' ? 'douban-' + (candidate as any)._douban_id : 'tmdb-' + candidate.tmdb_id"
              class="candidate-item"
              :class="{ selected: identifyDialog.selectedCandidate === candidate }"
              @click="identifyDialog.selectedCandidate = candidate"
            >
              <el-image
                :src="candidate.poster_url || 'https://via.placeholder.com/100x150'"
                fit="cover"
                style="width: 100px; height: 150px; border-radius: 4px"
              />
              <div class="candidate-info">
                <h4>
                  {{ candidate.title }} ({{ candidate.year || '未知年份' }})
                  <el-tag v-if="(candidate as any)._source === 'douban'" size="small" type="warning" style="margin-left: 5px">豆瓣</el-tag>
                </h4>
                <p v-if="candidate.original_title && candidate.original_title !== candidate.title">
                  原名: {{ candidate.original_title }}
                </p>
                <p>
                  <el-tag size="small" type="info">{{
                    candidate.media_type === 'movie' ? '电影' : '电视剧'
                  }}</el-tag>
                  <el-tag
                    v-if="candidate.rating_tmdb"
                    size="small"
                    type="warning"
                    style="margin-left: 5px"
                  >
                    评分: {{ candidate.rating_tmdb?.toFixed(1) }}
                  </el-tag>
                </p>
                <p v-if="candidate.genres?.length" style="margin-top: 5px">
                  <el-tag
                    v-for="genre in candidate.genres.slice(0, 3)"
                    :key="genre"
                    size="small"
                    style="margin-right: 5px"
                  >
                    {{ genre }}
                  </el-tag>
                </p>
                <p class="overview">{{ candidate.overview || '暂无简介' }}</p>
              </div>
            </div>
          </div>
        </el-card>
      </div>
      <template #footer>
        <el-button @click="identifyDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!identifyDialog.selectedCandidate"
          :loading="identifyDialog.linking"
          @click="confirmIdentify"
        >
          确认选择
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  Folder,
  ArrowDown,
  Search,
  InfoFilled,
  FolderOpened,
  Download,
  Delete,
  Document,
} from '@element-plus/icons-vue'
import type { MediaFile, TMDBCandidate } from '@/types/media'
import type { OrganizeConfig } from '@/types/organize'
import type { StorageMount } from '@/api/modules/storage'
import {
  getMediaFileList,
  scanDirectory,
  extractMediaInfo,
  organizeSingleFile,
  organizeMediaFiles,
  deleteMediaFile,
  identifyMediaFile,
  linkMediaFileToResource,
  searchTMDB,
  searchDouban,
  scrapeMediaFile,
  batchScrapeMediaFiles,
  generateNFO,
  MediaFileStatusLabels,
  MediaFileStatusTypes,
  formatFileSize,
  formatDuration
} from '@/api/modules/media'
import { getOrganizeConfigList } from '@/api/modules/organize'
import { getStorageMounts } from '@/api/modules/storage'

// 移动端检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value <= 768)
const handleResize = () => { windowWidth.value = window.innerWidth }

// 状态
const loading = ref(false)
const scanning = ref(false)
const files = ref<MediaFile[]>([])
const configs = ref<OrganizeConfig[]>([])
const storageMounts = ref<StorageMount[]>([])
const selectedIds = ref<number[]>([])
const selectedConfigId = ref<number | undefined>(undefined)

const filters = reactive({
  status: '',
  organized: undefined as boolean | undefined  // 默认显示全部文件
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const organizeDialog = reactive({
  visible: false,
  loading: false,  // 整理中的加载状态
  fileIds: [] as number[],
  configId: undefined as number | undefined,
  storageMountId: undefined as number | undefined,
  dryRun: false,
  force: false,  // 强制重新整理
  mediaType: '' as string,
  unifiedTableName: undefined as string | undefined,
  seasonNumber: undefined as number | undefined,
  episodeNumber: undefined as number | undefined
})

const identifyDialog = reactive({
  visible: false,
  fileId: undefined as number | undefined,
  loading: false,
  linking: false,
  parsedInfo: null as Record<string, any> | null,
  candidates: [] as TMDBCandidate[],
  selectedCandidate: null as TMDBCandidate | null
})

const manualSearch = reactive({
  title: '',
  year: undefined as number | undefined,
  media_type: 'movie',
  search_source: 'tmdb' as 'tmdb' | 'douban',
  loading: false
})

onMounted(() => {
  loadFiles()
  loadConfigs()
  loadStorageMounts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

async function loadFiles() {
  loading.value = true
  try {
    const queryParams: any = {
      skip: (pagination.page - 1) * pagination.size,
      limit: pagination.size,
      status: filters.status || undefined,
      organized: filters.organized,
      mount_type: 'download'
    }

    const res = await getMediaFileList(queryParams)
    files.value = res.data.items
    pagination.total = res.data.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载文件列表失败')
  } finally {
    loading.value = false
  }
}

async function loadConfigs() {
  try {
    const res = await getOrganizeConfigList({ limit: 100, is_enabled: true })
    configs.value = res.data.items
    // 如果有默认配置，自动选中第一个
    if (configs.value.length > 0 && !selectedConfigId.value) {
      const defaultConfig = configs.value.find((c) => c.is_default) || configs.value[0]
      selectedConfigId.value = defaultConfig.id
    }
  } catch (error: any) {
    ElMessage.error('加载配置失败')
  }
}

async function loadStorageMounts() {
  try {
    const res = await getStorageMounts({ mount_type: 'library', is_enabled: true })
    storageMounts.value = res.data.items
  } catch (error: any) {
    ElMessage.error('加载存储挂载点失败')
  }
}

async function scanDownloads() {
  scanning.value = true
  const label = '所有下载目录'
  try {
    const res = await scanDirectory({
      mount_type: 'download',
      recursive: true,
      scan_mode: 'incremental'
    })

    const executionId = (res.data as any).execution_id
    ElMessage.success(`${label}扫描任务已创建，正在后台执行...`)
    await pollTaskStatus(executionId, label)
  } catch (error: any) {
    ElMessage.error(error.message || `扫描${label}失败`)
    scanning.value = false
  }
}

async function pollTaskStatus(executionId: number, label: string) {
  const { getTaskExecution } = await import('@/api/modules/task')

  const poll = async () => {
    try {
      const taskRes = await getTaskExecution(executionId)
      const task = taskRes.data

      if (task.status === 'completed') {
        scanning.value = false
        const filesCreated = task.result?.files_created || 0
        ElMessage.success(`${label}扫描完成！创建了 ${filesCreated} 个媒体文件记录`)
        await loadFiles()
      } else if (task.status === 'failed') {
        scanning.value = false
        ElMessage.error(`${label}扫描失败: ${task.error_message || '未知错误'}`)
      } else if (task.status === 'running' || task.status === 'pending') {
        setTimeout(poll, 2000)
      } else {
        scanning.value = false
        ElMessage.warning(`${label}扫描${task.status === 'cancelled' ? '已取消' : '超时'}`)
      }
    } catch (error: any) {
      scanning.value = false
      ElMessage.error(`查询任务状态失败: ${error.message}`)
    }
  }

  await poll()
}

function handleSelectionChange(selection: MediaFile[]) {
  selectedIds.value = selection.map((item) => item.id)
}

function handleAction(command: string, id: number) {
  switch (command) {
    case 'identify':
      handleIdentify(id)
      break
    case 'extract':
      handleExtractInfo(id)
      break
    case 'organize':
      handleOrganize(id)
      break
    case 'scrape':
      handleScrape(id)
      break
    case 'generate-nfo':
      handleGenerateNFO(id)
      break
    case 'delete':
      handleDelete(id)
      break
  }
}


/**
 * Helper to get status type
 */
function getStatusType(status: string) {
  return MediaFileStatusTypes[status] as any
}

function getStatusLabel(status: string) {
  return MediaFileStatusLabels[status] || status
}

function getOrganizeModeLabel(mode: string) {
  const labels: Record<string, string> = {
    'hardlink': '硬链接',
    'symlink': '软链接',
    'move': '移动',
    'copy': '复制'
  }
  return labels[mode] || mode
}

// ========== 识别相关函数 ==========

async function handleIdentify(id: number) {
  identifyDialog.fileId = id
  identifyDialog.visible = true
  identifyDialog.loading = true
  identifyDialog.parsedInfo = null
  identifyDialog.candidates = []
  identifyDialog.selectedCandidate = null

  try {
    const res = await identifyMediaFile(id)
    identifyDialog.parsedInfo = res.data.parsed_info || null
    identifyDialog.candidates = res.data.candidates || []

    if (identifyDialog.parsedInfo) {
      manualSearch.title = identifyDialog.parsedInfo.title || ''
      manualSearch.year = identifyDialog.parsedInfo.year || undefined
      if (identifyDialog.parsedInfo.type === 'episode') {
        manualSearch.media_type = 'tv'
      } else {
        manualSearch.media_type = 'movie'
      }
    }

    if (res.data.auto_matched && res.data.candidates.length > 0) {
      identifyDialog.selectedCandidate = res.data.candidates[0]
      ElMessage.success('自动匹配成功，请确认是否正确')
    } else if (res.data.candidates.length === 0) {
      ElMessage.warning('未找到匹配结果，请尝试手动搜索')
    }

    if (res.data.error) {
      ElMessage.error(res.data.error)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '识别失败')
  } finally {
    identifyDialog.loading = false
  }
}

async function handleManualSearch() {
  if (!manualSearch.title) {
    ElMessage.warning('请输入标题')
    return
  }

  manualSearch.loading = true
  try {
    if (manualSearch.search_source === 'douban') {
      const res = await searchDouban({
        title: manualSearch.title,
        year: manualSearch.year,
        media_type: manualSearch.media_type
      })
      // 将豆瓣结果转换为统一的候选格式
      identifyDialog.candidates = (res.data.results || []).map((item: any) => ({
        tmdb_id: 0,
        title: item.title,
        original_title: '',
        year: item.year,
        overview: item.overview,
        poster_url: item.poster_url,
        rating_tmdb: item.rating_douban,
        genres: [],
        media_type: manualSearch.media_type,
        _source: 'douban' as const,
        _douban_id: item.douban_id,
      }))
    } else {
      const res = await searchTMDB({
        title: manualSearch.title,
        year: manualSearch.year,
        media_type: manualSearch.media_type
      })
      identifyDialog.candidates = (res.data.results || []).map((item: any) => ({
        ...item,
        _source: 'tmdb' as const,
      }))
    }
    identifyDialog.selectedCandidate = null

    if (identifyDialog.candidates.length === 0) {
      ElMessage.warning('未找到结果，请尝试调整搜索条件或切换来源')
    } else {
      ElMessage.success(`找到 ${identifyDialog.candidates.length} 个结果`)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '搜索失败')
  } finally {
    manualSearch.loading = false
  }
}

async function confirmIdentify() {
  if (!identifyDialog.selectedCandidate || !identifyDialog.fileId) {
    ElMessage.warning('请选择一个匹配项')
    return
  }

  identifyDialog.linking = true
  try {
    const candidate = identifyDialog.selectedCandidate as any
    if (candidate._source === 'douban') {
      ElMessage.warning('豆瓣搜索结果暂不支持直接关联，请使用搜索到的标题切换到 TMDB 来源重新搜索')
      identifyDialog.linking = false
      return
    }
    const res = await linkMediaFileToResource(identifyDialog.fileId!, {
      tmdb_id: candidate.tmdb_id,
      media_type: candidate.media_type
    })

    if (res.data.success) {
      ElMessage.success(res.data.message || '关联成功')
      identifyDialog.visible = false
      loadFiles()
    } else {
      ElMessage.error(res.data.message || '关联失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '关联失败')
  } finally {
    identifyDialog.linking = false
  }
}

// ========== 批量识别 ==========

async function handleBatchIdentify() {
  if (!selectedIds.value.length) return

  try {
    await ElMessageBox.confirm(
      `确定要识别 ${selectedIds.value.length} 个文件吗？`,
      '批量识别',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const loading = ElMessage({
      message: `正在识别 ${selectedIds.value.length} 个文件...`,
      type: 'info',
      duration: 0
    })

    for (const id of selectedIds.value) {
      try {
        await identifyMediaFile(id)
      } catch (error) {
        console.warn(`识别文件 ${id} 失败:`, error)
      }
    }

    loading.close()
    ElMessage.success('批量识别完成')
    loadFiles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '批量识别失败')
    }
  }
}

// ========== 整理相关函数 ==========

function handleOrganize(id: number) {
  const file = files.value.find((f) => f.id === id)
  organizeDialog.fileIds = [id]
  organizeDialog.mediaType = file?.media_type || ''
  organizeDialog.unifiedTableName = file?.unified_table_name
  organizeDialog.seasonNumber = file?.season_number
  organizeDialog.episodeNumber = file?.episode_number
  organizeDialog.dryRun = false
  // 如果文件已整理，默认开启强制整理
  organizeDialog.force = file?.organized || false

  // 优先使用下载任务关联的配置，否则使用默认配置
  if (file?.download_organize_config_id) {
    organizeDialog.configId = file.download_organize_config_id
  } else if (configs.value.length > 0) {
    const defaultConfig = configs.value.find((c) => c.is_default) || configs.value[0]
    organizeDialog.configId = defaultConfig.id
  }

  // 优先使用下载任务关联的存储挂载点，否则使用默认
  if (file?.download_storage_mount_id) {
    organizeDialog.storageMountId = file.download_storage_mount_id
  } else if (storageMounts.value.length > 0) {
    const defaultMount = storageMounts.value.find((m) => m.is_default) || storageMounts.value[0]
    organizeDialog.storageMountId = defaultMount.id
  }

  organizeDialog.visible = true
}

function handleBatchOrganize() {
  const selectedFiles = files.value.filter((f) => selectedIds.value.includes(f.id))
  const mediaTypes = new Set(selectedFiles.map((f) => f.media_type))

  organizeDialog.fileIds = [...selectedIds.value]
  organizeDialog.dryRun = false
  // 如果有任何文件已整理，默认开启强制整理
  organizeDialog.force = selectedFiles.some((f) => f.organized)
  
  const unifiedTableNames = new Set(selectedFiles.map((f) => f.unified_table_name).filter(Boolean))
  organizeDialog.unifiedTableName = unifiedTableNames.size === 1 ? Array.from(unifiedTableNames)[0] : undefined

  if (mediaTypes.size === 1 && (mediaTypes.has('tv') || mediaTypes.has('anime'))) {
    organizeDialog.mediaType = Array.from(mediaTypes)[0]
    organizeDialog.seasonNumber = undefined
    organizeDialog.episodeNumber = undefined
  } else {
    organizeDialog.mediaType = ''
    organizeDialog.seasonNumber = undefined
    organizeDialog.episodeNumber = undefined
  }

  // 对于批量整理，如果所有文件的配置一致则使用，否则使用默认
  const configIds = selectedFiles.map((f) => f.download_organize_config_id).filter(Boolean)
  const mountIds = selectedFiles.map((f) => f.download_storage_mount_id).filter(Boolean)

  if (configIds.length > 0 && new Set(configIds).size === 1) {
    organizeDialog.configId = configIds[0]
  } else if (configs.value.length > 0) {
    const defaultConfig = configs.value.find((c) => c.is_default) || configs.value[0]
    organizeDialog.configId = defaultConfig.id
  }

  if (mountIds.length > 0 && new Set(mountIds).size === 1) {
    organizeDialog.storageMountId = mountIds[0]
  } else if (storageMounts.value.length > 0) {
    const defaultMount = storageMounts.value.find((m) => m.is_default) || storageMounts.value[0]
    organizeDialog.storageMountId = defaultMount.id
  }

  organizeDialog.visible = true
}

async function confirmOrganize() {
  if (organizeDialog.fileIds.length === 1) {
    if (
      (organizeDialog.mediaType === 'tv' || organizeDialog.mediaType === 'anime') &&
      organizeDialog.unifiedTableName !== 'unified_movies' &&
      (!organizeDialog.seasonNumber || !organizeDialog.episodeNumber)
    ) {
      ElMessage.warning('请输入季数和集数信息')
      return
    }

    organizeDialog.loading = true
    try {
      const res = await organizeSingleFile(
        organizeDialog.fileIds[0],
        organizeDialog.configId,
        organizeDialog.dryRun,
        organizeDialog.force,
        organizeDialog.seasonNumber,
        organizeDialog.episodeNumber,
        organizeDialog.storageMountId
      )
      ElMessage.success(res.data.message || '整理成功')
      organizeDialog.visible = false
      loadFiles()
    } catch (error: any) {
      ElMessage.error(error.message || '整理失败')
    } finally {
      organizeDialog.loading = false
    }
  } else {
    const selectedFiles = files.value.filter((f) => organizeDialog.fileIds.includes(f.id))
    const tvFiles = selectedFiles.filter((f) => (f.media_type === 'tv' || f.media_type === 'anime') && f.unified_table_name !== 'unified_movies')
    const unidentifiedFiles = tvFiles.filter((f) => !f.season_number || !f.episode_number)

    if (unidentifiedFiles.length > 0) {
      try {
        await ElMessageBox.confirm(
          `检测到 ${unidentifiedFiles.length} 个文件缺少季集信息，将跳过这些文件。是否继续？`,
          '提示',
          {
            confirmButtonText: '继续',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
      } catch {
        return
      }
    }

    organizeDialog.loading = true
    try {
      const res = await organizeMediaFiles({
        file_ids: organizeDialog.fileIds,
        config_id: organizeDialog.configId,
        dry_run: organizeDialog.dryRun,
        force: organizeDialog.force,
        storage_mount_id: organizeDialog.storageMountId
      })
      const data = res.data as any
      ElMessage.success(`整理完成: 成功 ${data.success_count}, 失败 ${data.failed_count}`)
      organizeDialog.visible = false
      loadFiles()
    } catch (error: any) {
      ElMessage.error(error.message || '整理失败')
    } finally {
      organizeDialog.loading = false
    }
  }
}

// ========== 刮削与信息提取 ==========

async function handleExtractInfo(id: number) {
  try {
    await extractMediaInfo(id)
    ElMessage.success('信息提取成功')
    loadFiles()
  } catch (error: any) {
    ElMessage.error(error.message || '信息提取失败')
  }
}

async function handleScrape(id: number) {
  try {
    await ElMessageBox.confirm('确定要重新刮削此文件吗？将强制覆盖已有的海报、背景图和NFO文件', '重新刮削', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    const loading = ElMessage({
      message: '正在刮削...',
      type: 'info',
      duration: 0
    })

    const res = await scrapeMediaFile(id, selectedConfigId.value, true)
    loading.close()

    if (res.data.success) {
      ElMessage.success('刮削成功')
    } else {
      ElMessage.warning(`刮削部分失败: ${res.data.errors.join(', ')}`)
    }
    loadFiles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '刮削失败')
    }
  }
}

async function handleBatchScrape() {
  if (!selectedConfigId.value) {
    ElMessage.warning('请先选择一个整理配置')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要刮削 ${selectedIds.value.length} 个文件吗？将下载海报、背景图并生成NFO文件`,
      '批量刮削',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const loading = ElMessage({
      message: `正在刮削 ${selectedIds.value.length} 个文件...`,
      type: 'info',
      duration: 0
    })

    const res = await batchScrapeMediaFiles({
      file_ids: selectedIds.value,
      config_id: selectedConfigId.value
    })
    loading.close()

    const data = res.data as any
    ElMessage.success(`批量刮削完成: 成功 ${data.success_count}, 失败 ${data.failed_count}`)
    loadFiles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '批量刮削失败')
    }
  }
}

async function handleGenerateNFO(id: number) {
  try {
    const loading = ElMessage({
      message: '正在生成NFO...',
      type: 'info',
      duration: 0
    })

    const res = await generateNFO(id, selectedConfigId.value, true)
    loading.close()

    if (res.data.success) {
      ElMessage.success(`NFO生成成功: ${res.data.nfo_path}`)
    } else {
      ElMessage.error(`NFO生成失败: ${res.data.error}`)
    }
    loadFiles()
  } catch (error: any) {
    ElMessage.error(error.message || '生成NFO失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此文件记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteMediaFile(id, false)
    ElMessage.success('删除成功')
    loadFiles()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.candidates-list {
  max-height: 400px;
  overflow-y: auto;
}

.candidate-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border: 2px solid var(--nf-border-base);
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

.candidate-item:hover {
  border-color: var(--nf-primary);
  background-color: var(--nf-bg-hover);
}

.candidate-item.selected {
  border-color: var(--nf-success);
  background-color: var(--nf-bg-overlay);
}

.candidate-info {
  flex: 1;
}

.candidate-info h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: var(--nf-text-primary);
}

.candidate-info p {
  margin: 5px 0;
  font-size: 14px;
  color: var(--nf-text-regular);
}

.candidate-info .overview {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  color: var(--nf-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.file-subtitle {
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin-top: 2px;
}

.delete-item {
  color: var(--nf-danger) !important;
}

/* Mobile 工具栏 */
.mobile-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-filters {
  display: flex;
  gap: 8px;
}

.mobile-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Mobile 文件卡片 */
.file-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-card {
  border: 1px solid var(--nf-border-base);
  border-radius: 8px;
  padding: 12px;
  background: var(--nf-bg-container);
}

.file-card-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}

.file-card-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--nf-text-primary);
  word-break: break-all;
  line-height: 1.4;
}

.file-card-subtitle {
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin-bottom: 2px;
}

.file-card-path {
  font-size: 11px;
  color: var(--nf-text-placeholder);
  margin-bottom: 8px;
  word-break: break-all;
}

.file-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
}

.file-card-size {
  font-size: 12px;
  color: var(--nf-text-secondary);
  flex-shrink: 0;
}

.file-card-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.file-card-organized-path {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--nf-border-lighter);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.organized-path-text {
  font-size: 11px;
  color: var(--nf-text-secondary);
  word-break: break-all;
}

.file-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--nf-text-placeholder);
  font-size: 14px;
}
</style>
