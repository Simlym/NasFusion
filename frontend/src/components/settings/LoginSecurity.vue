<template>
  <div class="settings-section">
    <div class="section-header">
      <div>
        <h3>登录安全</h3>
        <p class="section-description">查看登录历史记录，监控账户安全状态</p>
      </div>
      <div class="header-actions">
        <el-button
          v-if="isAdmin"
          type="danger"
          plain
          size="small"
          @click="handleCleanup"
        >
          清理旧记录
        </el-button>
        <el-radio-group v-model="viewMode" size="small" @change="handleViewModeChange">
          <el-radio-button value="my">我的记录</el-radio-button>
          <el-radio-button v-if="isAdmin" value="all">所有用户</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 安全概览 -->
    <div class="security-overview">
      <div class="stat-card">
        <div class="stat-icon success">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.successCount }}</div>
          <div class="stat-label">成功登录</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon warning">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.failedCount }}</div>
          <div class="stat-label">失败尝试</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon danger">
          <el-icon><Lock /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.lockedCount }}</div>
          <div class="stat-label">锁定次数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon info">
          <el-icon><Location /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.uniqueIps }}</div>
          <div class="stat-label">不同 IP</div>
        </div>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filter-container">
      <el-select v-model="filters.status" placeholder="登录状态" clearable @change="loadHistory">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="锁定" value="locked" />
      </el-select>
    </div>

    <!-- 登录历史列表 -->
    <el-table v-loading="loading" :data="records" style="width: 100%">
      <el-table-column v-if="viewMode === 'all'" prop="username" label="用户" width="120" />
      <el-table-column prop="login_status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.login_status === 'success'" type="success" size="small">成功</el-tag>
          <el-tag v-else-if="row.login_status === 'failed'" type="warning" size="small">失败</el-tag>
          <el-tag v-else-if="row.login_status === 'locked'" type="danger" size="small">锁定</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP 地址" min-width="150">
        <template #default="{ row }">
          <span class="ip-text">{{ row.ip_address || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="位置" min-width="160">
        <template #default="{ row }">
          <span>{{ formatLocation(row.location) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="user_agent" label="浏览器" min-width="180">
        <template #default="{ row }">
          <el-tooltip
            v-if="row.user_agent"
            :content="row.user_agent"
            placement="top"
            :show-after="500"
          >
            <span class="ua-text">{{ parseBrowser(row.user_agent) }}</span>
          </el-tooltip>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="failure_reason" label="失败原因" min-width="140">
        <template #default="{ row }">
          <span v-if="row.failure_reason" class="failure-reason">{{ row.failure_reason }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="login_at" label="时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.login_at) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && records.length === 0" description="暂无登录记录" style="margin-top: 20px" />

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.page_size"
      class="pagination"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="loadHistory"
      @size-change="loadHistory"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Warning, Lock, Location } from '@element-plus/icons-vue'
import type { LoginHistoryRecord } from '@/types'
import { getMyLoginHistory, getAllLoginHistory, cleanupLoginHistory } from '@/api/modules/loginHistory'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.user?.role === 'admin')

// 视图模式
const viewMode = ref<'my' | 'all'>('my')

// 数据
const loading = ref(false)
const records = ref<LoginHistoryRecord[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  page_size: 20
})
const filters = reactive({
  status: undefined as string | undefined
})

// 统计数据
const stats = reactive({
  successCount: 0,
  failedCount: 0,
  lockedCount: 0,
  uniqueIps: 0
})

// 加载登录历史
async function loadHistory() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      status: filters.status
    }

    const response = viewMode.value === 'all'
      ? await getAllLoginHistory(params)
      : await getMyLoginHistory(params)

    if (response?.data) {
      records.value = response.data.items
      total.value = response.data.total
    }
  } catch (error: any) {
    ElMessage.error(error.message || '加载登录历史失败')
  } finally {
    loading.value = false
  }
}

// 加载统计数据
async function loadStats() {
  try {
    // 获取最近的记录用于统计
    const params = { page: 1, page_size: 100 }
    const response = viewMode.value === 'all'
      ? await getAllLoginHistory(params)
      : await getMyLoginHistory(params)

    if (response?.data) {
      const items = response.data.items
      stats.successCount = items.filter(r => r.login_status === 'success').length
      stats.failedCount = items.filter(r => r.login_status === 'failed').length
      stats.lockedCount = items.filter(r => r.login_status === 'locked').length
      const ips = new Set(items.filter(r => r.ip_address).map(r => r.ip_address))
      stats.uniqueIps = ips.size
    }
  } catch (error) {
    // 静默失败，统计数据不影响主功能
  }
}

// 切换视图模式
function handleViewModeChange() {
  pagination.page = 1
  loadHistory()
  loadStats()
}

// 清理旧记录
async function handleCleanup() {
  try {
    await ElMessageBox.confirm(
      '将清理 90 天前的登录记录，此操作不可恢复。是否继续？',
      '清理旧记录',
      { type: 'warning', confirmButtonText: '确认清理', cancelButtonText: '取消' }
    )
    const response = await cleanupLoginHistory(90)
    if (response?.data) {
      ElMessage.success(response.data.message)
      loadHistory()
      loadStats()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '清理失败')
    }
  }
}

// 格式化日期
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化位置
function formatLocation(location: string | null | undefined): string {
  if (!location) return '未知'
  return location.replace(/\|/g, ' ')
}

// 解析浏览器信息
function parseBrowser(ua: string): string {
  if (!ua) return '-'
  // 简单解析常见浏览器
  if (ua.includes('Edg/')) return 'Edge'
  if (ua.includes('Chrome/') && !ua.includes('Edg/')) return 'Chrome'
  if (ua.includes('Firefox/')) return 'Firefox'
  if (ua.includes('Safari/') && !ua.includes('Chrome/')) return 'Safari'
  if (ua.includes('Opera') || ua.includes('OPR/')) return 'Opera'
  // 截取前40个字符
  return ua.substring(0, 40) + (ua.length > 40 ? '...' : '')
}

onMounted(() => {
  loadHistory()
  loadStats()
})
</script>

<style scoped lang="scss">
.settings-section {
  padding: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;

  h3 {
    margin: 0 0 4px 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text-color-primary);
  }

  .section-description {
    margin: 0;
    font-size: 13px;
    color: var(--text-color-secondary);
  }
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.security-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;

  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-color);
  border: 1px solid var(--border-color-light);
  border-radius: 8px;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--border-color);
  }
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;

  &.success {
    background: rgba(103, 194, 58, 0.1);
    color: #67c23a;
  }

  &.warning {
    background: rgba(230, 162, 60, 0.1);
    color: #e6a23c;
  }

  &.danger {
    background: rgba(245, 108, 108, 0.1);
    color: #f56c6c;
  }

  &.info {
    background: rgba(64, 158, 255, 0.1);
    color: #409eff;
  }
}

.stat-content {
  .stat-value {
    font-size: 22px;
    font-weight: 600;
    color: var(--text-color-primary);
    line-height: 1.2;
  }

  .stat-label {
    font-size: 12px;
    color: var(--text-color-secondary);
    margin-top: 2px;
  }
}

.filter-container {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;

  :deep(.el-select) {
    width: 160px;
  }
}

.ip-text {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  color: var(--text-color-regular);
}

.ua-text {
  font-size: 13px;
  color: var(--text-color-regular);
  cursor: help;
}

.failure-reason {
  font-size: 13px;
  color: var(--el-color-warning);
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
