<template>
  <div class="page-container">
    <!-- 顶部信息卡片 -->
    <div class="info-card">
      <div class="info-item">
        <div class="info-label">文件路径</div>
        <div class="info-value">{{ fileInfo?.file_path || '-' }}</div>
      </div>
      <div class="info-item">
        <div class="info-label">文件大小</div>
        <div class="info-value">{{ fileInfo?.file_size_mb || 0 }} MB</div>
      </div>
      <div class="info-item">
        <div class="info-label">日志总行数</div>
        <div class="info-value">{{ fileInfo?.line_count || 0 }} 行</div>
      </div>
      <div class="info-item">
        <div class="info-label">最后更新</div>
        <div class="info-value">{{ formatLastModified(fileInfo?.last_modified) }}</div>
      </div>
    </div>

    <!-- 过滤器区域 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item">
          <label>日志级别</label>
          <el-select
            v-model="filters.level"
            placeholder="全部级别"
            clearable
            size="default"
            style="width: 150px"
            @change="handleFilterChange"
          >
            <el-option label="DEBUG" value="DEBUG" />
            <el-option label="INFO" value="INFO" />
            <el-option label="WARNING" value="WARNING" />
            <el-option label="ERROR" value="ERROR" />
            <el-option label="CRITICAL" value="CRITICAL" />
          </el-select>
        </div>

        <div class="filter-item">
          <label>关键词搜索</label>
          <el-input
            v-model="filters.keyword"
            placeholder="搜索日志内容"
            clearable
            size="default"
            style="width: 300px"
            @keyup.enter="handleFilterChange"
          >
            <template #append>
              <el-button :icon="Search" @click="handleFilterChange" />
            </template>
          </el-input>
        </div>

        <div class="filter-item">
          <el-checkbox v-model="filters.reverse" @change="handleFilterChange">
            倒序显示（最新在前）
          </el-checkbox>
        </div>

        <div class="filter-actions">
          <el-button :icon="Refresh" :loading="loading" @click="loadLogs">
            刷新
          </el-button>
          <el-button :icon="Delete" @click="handleClearFilters">
            清除筛选
          </el-button>
          <el-button type="danger" :icon="Delete" @click="handleCleanLogs">
            清空日志
          </el-button>
        </div>

        <div class="filter-auto-refresh">
          <el-switch
            v-model="autoRefresh"
            active-text="自动刷新 (5s)"
            @change="handleAutoRefreshChange"
          />
        </div>
      </div>
    </div>

    <!-- 日志表格 -->
    <div v-loading="loading" class="logs-table-container">
      <el-table
        :data="logs"
        class="logs-table"
        height="100%"
        :style="{ width: '100%' }"
        :header-cell-style="{
          background: 'var(--nf-bg-elevated)',
          color: 'var(--nf-text-primary)',
          fontWeight: '600',
          fontSize: '13px'
        }"
        stripe
      >

        <el-table-column prop="line_number" label="行号" width="80" align="center" />

        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            <span class="log-timestamp">{{ row.timestamp || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="level" label="级别" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.level"
              :type="getLogLevelType(row.level)"
              size="small"
              effect="light"
            >
              {{ row.level }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="logger" label="Logger" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="log-logger">{{ row.logger || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="message" label="消息" min-width="400">
          <template #default="{ row }">
            <div class="log-message" :class="{ 'has-keyword': filters.keyword }">
              {{ row.message }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              text
              size="small"
              @click="handleViewRaw(row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[50, 100, 200, 500, 1000]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadLogs"
          @size-change="handlePageSizeChange"
        />
      </div>
    </div>

    <!-- 原文查看对话框 -->
    <el-dialog
      v-model="rawDialogVisible"
      title="日志原文"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="raw-log-container">
        <pre class="raw-log-content" v-html="highlightedLog"></pre>
      </div>
      <template #footer>
        <el-button @click="rawDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleCopyRaw">复制</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Delete } from '@element-plus/icons-vue'
import { getSystemLogs, getLogFileInfo, cleanSystemLogs, type LogEntry, type LogFileInfo } from '@/api/modules/log'
import hljs from 'highlight.js/lib/core'
import json from 'highlight.js/lib/languages/json'
import 'highlight.js/styles/github-dark.css' // 引入样式，需要确认项目是否安装了 highlight.js

hljs.registerLanguage('json', json)


// 数据
const logs = ref<LogEntry[]>([])
const fileInfo = ref<LogFileInfo | null>(null)
const loading = ref(false)
const rawDialogVisible = ref(false)
const currentRawLog = ref('')
const autoRefresh = ref(false)
let refreshTimer: number | null = null

// 过滤器
const filters = reactive({
  level: '',
  keyword: '',
  reverse: true
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 100,
  total: 0
})

// 日志级别样式映射
const getLogLevelType = (level: string) => {
  const levelUpper = level?.toUpperCase()
  switch (levelUpper) {
    case 'DEBUG':
      return 'info'
    case 'INFO':
      return 'success'
    case 'WARNING':
      return 'warning'
    case 'ERROR':
    case 'CRITICAL':
      return 'danger'
    default:
      return ''
  }
}

// 格式化最后修改时间
const formatLastModified = (timestamp?: number) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

// 加载日志文件信息
const loadFileInfo = async () => {
  try {
    const res = await getLogFileInfo()
    if (res?.data) {
      fileInfo.value = res.data
    }
  } catch (error: any) {
    console.error('Failed to load log file info:', error)
  }
}

// 加载日志列表
const loadLogs = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      level: filters.level || undefined,
      keyword: filters.keyword || undefined,
      reverse: filters.reverse
    }

    const res = await getSystemLogs(params)
    if (res?.data) {
      logs.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error: any) {
    console.error('Failed to load logs:', error)
    ElMessage.error(error.response?.data?.detail || '加载日志失败')
  } finally {
    loading.value = false
  }
}

// 处理过滤器变化
const handleFilterChange = () => {
  pagination.page = 1
  loadLogs()
}


// 处理页面大小变化
const handlePageSizeChange = () => {
  pagination.page = 1
  loadLogs()
}

// 清除筛选条件
const handleClearFilters = () => {
  filters.level = ''
  filters.keyword = ''
  filters.reverse = true
  pagination.page = 1
  loadLogs()
}

// 清空日志
const handleCleanLogs = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有系统日志吗？此操作不可恢复。',
      '确认清空',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await cleanSystemLogs()
    ElMessage.success('系统日志已清空')
    
    // 重新加载
    loadFileInfo()
    loadLogs()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to clean logs:', error)
      ElMessage.error(error.response?.data?.detail || '清空日志失败')
    }
  }
}

// 查看详情
const handleViewRaw = (row: LogEntry) => {
  currentRawLog.value = row.raw
  rawDialogVisible.value = true
}

// 高亮JSON
const highlightedLog = computed(() => {
  if (!currentRawLog.value) return ''
  try {
    // 尝试格式化JSON
    if (currentRawLog.value.trim().startsWith('{')) {
      const obj = JSON.parse(currentRawLog.value)
      const formatted = JSON.stringify(obj, null, 2)
      return hljs.highlight(formatted, { language: 'json' }).value
    }
  } catch (e) {
    // ignore
  }
  return currentRawLog.value
})

const handleAutoRefreshChange = (val: boolean) => {
  if (val) {
    refreshTimer = window.setInterval(() => {
      // 只有在第一页且没有搜索关键词时才自动刷新
      if (pagination.page === 1 && !filters.keyword && !filters.level) {
        loadLogs(true) // true for silent refresh
      }
    }, 5000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 复制原文
const handleCopyRaw = () => {
  navigator.clipboard.writeText(currentRawLog.value)
  ElMessage.success('已复制到剪贴板')
  rawDialogVisible.value = false
}

// 初始化
onMounted(() => {
  loadFileInfo()
  loadLogs()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped lang="scss">
.page-container {
  padding: var(--nf-spacing-lg);
  background: var(--nf-bg-page);
  height: 100vh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

// 信息卡片
.info-card {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--nf-spacing-base);
  margin-bottom: var(--nf-spacing-lg);

  .info-item {
    padding: var(--nf-spacing-base);
    background: var(--nf-bg-container);
    border: 1px solid var(--nf-border-base);
    border-radius: var(--nf-radius-base);
    transition: all var(--nf-transition-base) var(--nf-ease-in-out);

    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--nf-shadow-md);
      border-color: var(--nf-border-light);
    }

    .info-label {
      font-size: var(--nf-font-size-small);
      color: var(--nf-text-secondary);
      margin-bottom: var(--nf-spacing-sm);
    }

    .info-value {
      font-size: var(--nf-font-size-h4);
      font-weight: var(--nf-font-weight-semibold);
      color: var(--nf-text-primary);
      word-break: break-all;
    }
  }
}

// 过滤器区域
.filter-section {
  margin-bottom: var(--nf-spacing-lg);
  padding: var(--nf-spacing-lg);
  background: var(--nf-bg-elevated);
  border-radius: var(--nf-radius-lg);
  border: 1px solid var(--nf-border-base);
  box-shadow: var(--nf-shadow-sm);

  .filter-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--nf-spacing-base);
    align-items: flex-end;

    .filter-item {
      display: flex;
      flex-direction: column;
      gap: var(--nf-spacing-sm);

      label {
        font-size: var(--nf-font-size-small);
        font-weight: var(--nf-font-weight-medium);
        color: var(--nf-text-secondary);
      }
    }

    .filter-actions {
      margin-left: auto;
      display: flex;
      gap: var(--nf-spacing-sm);
    }

    .filter-auto-refresh {
      display: flex;
      align-items: center;
    }
  }
}

// 日志表格容器
.logs-table-container {
  background: var(--nf-bg-elevated);
  border-radius: var(--nf-radius-lg);
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .logs-table {
    border-radius: var(--nf-radius-base);
    overflow: hidden;

    :deep(.el-table__row) {
      cursor: pointer;
      transition: all var(--nf-transition-fast) var(--nf-ease-default);

      &:hover {
        background-color: var(--nf-bg-overlay) !important;
      }
    }
  }

  .log-timestamp {
    font-family: var(--nf-font-family-mono);
    font-size: var(--nf-font-size-mini);
    color: var(--nf-text-secondary);
  }

  .log-logger {
    font-size: var(--nf-font-size-mini);
    color: var(--nf-text-placeholder);
  }

  .log-message {
    font-size: var(--nf-font-size-small);
    color: var(--nf-text-regular);
    line-height: var(--nf-line-height-base);
    white-space: pre-wrap;
    word-break: break-word;

    &.has-keyword {
      font-weight: var(--nf-font-weight-medium);
    }
  }
}

// 分页容器
.pagination-container {
  margin-top: var(--nf-spacing-lg);
  display: flex;
  justify-content: center;
}

// 原文查看对话框
.raw-log-container {
  max-height: 500px;
  overflow-y: auto;
  background: var(--nf-bg-base);
  border-radius: var(--nf-radius-base);
  padding: var(--nf-spacing-base);
  border: 1px solid var(--nf-border-base);

  .raw-log-content {
    margin: 0;
    font-family: var(--nf-font-family-mono);
    font-size: var(--nf-font-size-small);
    line-height: var(--nf-line-height-base);
    color: var(--nf-text-regular);
    white-space: pre-wrap;
    word-break: break-all;
  }
}
</style>
