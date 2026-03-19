<template>
  <div class="download-task-list">
    <!-- 统计卡片 -->
    <el-row :gutter="12" style="margin-bottom: 20px">
      <el-col :xs="12" :span="6">
        <el-card shadow="hover">
          <el-statistic title="总任务数" :value="stats.total" />
        </el-card>
      </el-col>
      <el-col :xs="12" :span="6">
        <el-card shadow="hover">
          <el-statistic title="下载中" :value="stats.downloading">
            <template #suffix>
              <el-icon color="#409eff"><Download /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :span="6" style="margin-top: 0">
        <el-card shadow="hover">
          <el-statistic title="做种中" :value="stats.seeding">
            <template #suffix>
              <el-icon color="#67c23a"><Upload /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :span="6">
        <el-card shadow="hover">
          <el-statistic title="已完成" :value="stats.completed">
            <template #suffix>
              <el-icon color="#67c23a"><Check /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>下载任务</span>
          <div>
            <el-button type="primary" :icon="Refresh" @click="refreshTasks">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选器 -->
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :xs="24" :span="6">
          <el-select v-model="filters.status" placeholder="状态筛选" clearable style="width: 100%" @change="loadTasks">
            <el-option label="全部" value="" />
            <el-option label="等待下载" value="pending" />
            <el-option label="下载中" value="downloading" />
            <el-option label="已暂停" value="paused" />
            <el-option label="下载完成" value="completed" />
            <el-option label="做种中" value="seeding" />
            <el-option label="错误" value="error" />
          </el-select>
        </el-col>
        <el-col :xs="24" :span="6" :style="isMobile ? 'margin-top: 8px' : ''">
          <el-select
            v-model="filters.downloader_config_id"
            placeholder="下载器筛选"
            clearable
            style="width: 100%"
            @change="loadTasks"
          >
            <el-option label="全部下载器" value="" />
            <el-option
              v-for="downloader in downloaders"
              :key="downloader.id"
              :label="downloader.name"
              :value="downloader.id"
            />
          </el-select>
        </el-col>
      </el-row>

      <!-- PC: 任务表格 -->
      <el-table v-if="!isMobile" v-loading="loading" :data="tasks" style="width: 100%">
        <el-table-column label="任务名称" min-width="300">
          <template #default="{ row }">
            <div>
              <div class="resource-title">{{ row.torrent_name }}</div>
              <div v-if="row.subtitle" class="resource-subtitle">{{ row.subtitle }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="getProgressStatus(row.status)" />
            <div class="progress-meta">
              {{ formatSize(row.downloaded_size) }} / {{ formatSize(row.total_size) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="速度" width="150">
          <template #default="{ row }">
            <div>
              <el-icon><Download /></el-icon>
              {{ formatSpeed(row.download_speed) }}
            </div>
            <div>
              <el-icon><Upload /></el-icon>
              {{ formatSpeed(row.upload_speed) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="分享率" width="100">
          <template #default="{ row }">
            <el-tag :type="row.ratio >= 1 ? 'success' : 'warning'" size="small">
              {{ row.ratio.toFixed(2) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="TaskStatusTypes[row.status as TaskStatus]" size="small">
              {{ TaskStatusLabels[row.status as TaskStatus] }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="HR" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.has_hr" type="warning" size="small">HR</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'downloading' || row.status === 'seeding'"
              link
              type="warning"
              size="small"
              @click="pauseTask(row.id)"
            >
              暂停
            </el-button>
            <el-button
              v-if="row.status === 'paused'"
              link
              type="success"
              size="small"
              @click="resumeTask(row.id)"
            >
              恢复
            </el-button>
            <el-button link type="primary" size="small" @click="syncTask(row.id)">同步</el-button>
            <el-button link type="danger" size="small" @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Mobile: 任务卡片列表 -->
      <div v-else v-loading="loading" class="task-card-list">
        <div v-if="tasks.length === 0 && !loading" class="task-empty">暂无下载任务</div>
        <div v-for="row in tasks" :key="row.id" class="task-card">
          <div class="task-card-header">
            <div class="task-card-name">{{ row.torrent_name }}</div>
            <div class="task-card-badges">
              <el-tag :type="TaskStatusTypes[row.status as TaskStatus]" size="small">
                {{ TaskStatusLabels[row.status as TaskStatus] }}
              </el-tag>
              <el-tag v-if="row.has_hr" type="warning" size="small">HR</el-tag>
            </div>
          </div>
          <el-progress :percentage="row.progress" :status="getProgressStatus(row.status)" style="margin: 8px 0 4px" />
          <div class="task-card-meta">
            <span>{{ formatSize(row.downloaded_size) }} / {{ formatSize(row.total_size) }}</span>
            <span>比率: {{ row.ratio.toFixed(2) }}</span>
          </div>
          <div class="task-card-speed">
            <span><el-icon><Download /></el-icon> {{ formatSpeed(row.download_speed) }}</span>
            <span><el-icon><Upload /></el-icon> {{ formatSpeed(row.upload_speed) }}</span>
          </div>
          <div class="task-card-actions">
            <el-button
              v-if="row.status === 'downloading' || row.status === 'seeding'"
              type="warning"
              size="small"
              @click="pauseTask(row.id)"
            >暂停</el-button>
            <el-button
              v-if="row.status === 'paused'"
              type="success"
              size="small"
              @click="resumeTask(row.id)"
            >恢复</el-button>
            <el-button type="primary" size="small" @click="syncTask(row.id)">同步</el-button>
            <el-button type="danger" size="small" @click="deleteTask(row)">删除</el-button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <el-pagination
        v-if="!isMobile"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="loadTasks"
        @current-change="loadTasks"
      />
      <el-pagination
        v-else
        v-model:current-page="pagination.page"
        :total="pagination.total"
        :page-size="pagination.pageSize"
        layout="prev, pager, next"
        small
        style="margin-top: 16px; justify-content: center"
        @current-change="loadTasks"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Download,
  Upload,
  Check,
  Refresh,
} from '@element-plus/icons-vue'
import {
  getDownloadTaskList,
  syncDownloadTaskStatus,
  batchSyncTasks,
  controlDownloadTask,
  getDownloaderList,
  type DownloadTask,
  type DownloaderConfig,
  type TaskStatus,
  TaskStatusLabels,
  TaskStatusTypes
} from '@/api/modules/download'
import { formatSize, formatSpeed, formatDateTime } from '@/utils/format'

// 状态
const loading = ref(false)
const tasks = ref<DownloadTask[]>([])
const downloaders = ref<DownloaderConfig[]>([])

// 统计数据
const stats = reactive({
  total: 0,
  downloading: 0,
  seeding: 0,
  completed: 0
})

// 筛选条件
const filters = reactive({
  status: '',
  downloader_config_id: '' as number | string
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 移动端检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value <= 768)
const handleResize = () => { windowWidth.value = window.innerWidth }

// 自动刷新定时器
let autoRefreshTimer: number | null = null

// 获取进度条状态
function getProgressStatus(status: string) {
  if (status === 'completed' || status === 'seeding') return 'success'
  if (status === 'error') return 'exception'
  if (status === 'paused') return 'warning'
  return undefined
}

// 加载任务列表
async function loadTasks() {
  loading.value = true
  try {
    const res = await getDownloadTaskList({
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      status: filters.status || undefined,
      downloader_config_id: filters.downloader_config_id ? Number(filters.downloader_config_id) : undefined
    })

    tasks.value = res.data.items
    pagination.total = res.data.total

    // 更新统计
    updateStats(res.data.items)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载任务列表失败')
  } finally {
    loading.value = false
  }
}

// 更新统计数据
function updateStats(taskList: DownloadTask[]) {
  stats.total = taskList.length
  stats.downloading = taskList.filter((t) => t.status === 'downloading').length
  stats.seeding = taskList.filter((t) => t.status === 'seeding').length
  stats.completed = taskList.filter((t) => t.status === 'completed').length
}

// 加载下载器列表
async function loadDownloaders() {
  try {
    const res = await getDownloaderList({ is_enabled: true })
    downloaders.value = res.data.items
  } catch (error: any) {
    console.error('加载下载器列表失败:', error)
  }
}

// 刷新任务（批量同步状态）
async function refreshTasks() {
  if (tasks.value.length === 0) {
    loadTasks()
    return
  }

  loading.value = true
  try {
    // 同步活跃任务（pending、downloading、seeding）
    const activeTaskIds = tasks.value
      .filter((t) => t.status === 'pending' || t.status === 'downloading' || t.status === 'seeding')
      .map((t) => t.id)

    if (activeTaskIds.length > 0) {
      await batchSyncTasks(activeTaskIds)
    }

    // 重新加载列表
    await loadTasks()
    ElMessage.success('任务状态已刷新')
  } catch (error: any) {
    ElMessage.error('刷新失败')
  } finally {
    loading.value = false
  }
}

// 同步单个任务状态
async function syncTask(id: number) {
  try {
    await syncDownloadTaskStatus(id)
    await loadTasks()
    ElMessage.success('任务状态已同步')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '同步失败')
  }
}

// 暂停任务
async function pauseTask(id: number) {
  try {
    await controlDownloadTask(id, { action: 'pause' })
    await loadTasks()
    ElMessage.success('任务已暂停')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '暂停失败')
  }
}

// 恢复任务
async function resumeTask(id: number) {
  try {
    await controlDownloadTask(id, { action: 'resume' })
    await loadTasks()
    ElMessage.success('任务已恢复')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '恢复失败')
  }
}

// 删除任务
async function deleteTask(task: DownloadTask) {
  try {
    const action = await ElMessageBox.confirm('是否同时删除已下载的文件？', '删除任务', {
      distinguishCancelAndClose: true,
      confirmButtonText: '删除文件',
      cancelButtonText: '保留文件',
      type: 'warning'
    })

    const deleteFiles = action === 'confirm'
    await controlDownloadTask(task.id, { action: 'delete', delete_files: deleteFiles })
    await loadTasks()
    ElMessage.success('任务已删除')
  } catch (error: any) {
    if (error === 'cancel') {
      // 用户选择保留文件
      try {
        await controlDownloadTask(task.id, { action: 'delete', delete_files: false })
        await loadTasks()
        ElMessage.success('任务已删除（文件已保留）')
      } catch (err: any) {
        ElMessage.error(err.response?.data?.detail || '删除失败')
      }
    } else if (error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 启动自动刷新
function startAutoRefresh() {
  autoRefreshTimer = window.setInterval(() => {
    // 在有活跃任务时刷新（包括 pending 状态，防止初始状态显示错误）
    const hasActiveTasks = tasks.value.some(
      (t) => t.status === 'downloading' || t.status === 'seeding' || t.status === 'pending'
    )
    if (hasActiveTasks) {
      refreshTasks()
    }
  }, 30000) // 每30秒刷新一次
}

// 停止自动刷新
function stopAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

// 组件挂载
onMounted(() => {
  loadTasks()
  loadDownloaders()
  startAutoRefresh()
  window.addEventListener('resize', handleResize)
})

// 组件卸载
onUnmounted(() => {
  stopAutoRefresh()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
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

.progress-meta {
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin-top: 4px;
}

/* 移动端任务卡片列表 */
.task-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  border: 1px solid var(--nf-border-base);
  border-radius: 8px;
  padding: 12px;
  background: var(--nf-bg-container);
}

.task-card-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}

.task-card-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--nf-text-primary);
  word-break: break-all;
  line-height: 1.4;
}

.task-card-badges {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.task-card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin-bottom: 4px;
}

.task-card-speed {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin-bottom: 10px;
}

.task-card-speed .el-icon {
  vertical-align: middle;
  font-size: 12px;
}

.task-card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.task-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--nf-text-placeholder);
  font-size: 14px;
}
</style>
