<template>
  <div class="settings-section">
    <!-- 页面标题和操作 -->
    <div class="page-header">
      <div class="header-left">
        <h3 class="section-title">存储挂载点管理</h3>
        <p class="section-description">管理下载目录和媒体库目录，支持多盘聚合与硬链接优化</p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="handleAddMount">
          <el-icon><Plus /></el-icon>
          添加挂载点
        </el-button>
        <el-button :loading="refreshing" @click="handleRefreshAll">
          <el-icon><RefreshRight /></el-icon>
          刷新磁盘信息
        </el-button>
      </div>
    </div>


    <!-- Tab 切换 -->
    <el-card class="main-card">
      <el-tabs v-model="activeTab">
        <!-- 按磁盘查看 -->
        <el-tab-pane label="按磁盘查看" name="by-disk">
          <div v-loading="loading" class="tab-content">
            <div v-if="groupedByDevice.length === 0" class="empty-state">
              <el-empty description="暂无挂载点数据">
                <el-button type="primary" @click="handleAddMount">添加挂载点</el-button>
              </el-empty>
            </div>
            <el-collapse v-else v-model="expandedDevices">
              <el-collapse-item
                v-for="device in groupedByDevice"
                :key="device.volume_name"
                :name="device.volume_name"
              >
                <template #title>
                  <div class="device-header">
                    <div class="device-info">
                      <el-icon><HardDrive /></el-icon>
                      <span class="device-name">{{ device.volume_name }}</span>
                      <el-tag size="small" type="info">{{ device.downloadMounts.length + device.libraryMounts.length }} 个挂载点</el-tag>
                    </div>
                    <div v-if="device.total_space" class="device-space">
                      <el-progress
                        :percentage="getUsagePercent(device.used_space, device.total_space)"
                        :color="getSpaceColor(device.used_space / device.total_space)"
                        :stroke-width="8"
                        style="width: 200px"
                      />
                      <span class="space-text">
                        {{ formatSize(device.free_space) }} / {{ formatSize(device.total_space) }} 可用
                      </span>
                    </div>
                  </div>
                </template>

                <!-- 下载挂载点 -->
                <div v-if="device.downloadMounts.length > 0" class="mount-section">
                  <h4 class="sub-section-title">
                    <el-icon><Download /></el-icon>
                    下载目录 ({{ device.downloadMounts.length }})
                  </h4>
                  <MountTable :mounts="device.downloadMounts" @update="handleUpdateMount" @refresh="handleRefreshMount" @edit="handleEditMount" @delete="handleDeleteMount" />
                </div>
 
                <!-- 媒体库挂载点 -->
                <div v-if="device.libraryMounts.length > 0" class="mount-section">
                  <h4 class="sub-section-title">
                    <el-icon><Film /></el-icon>
                    媒体库目录 ({{ device.libraryMounts.length }})
                  </h4>
                  <MountTable :mounts="device.libraryMounts" @update="handleUpdateMount" @refresh="handleRefreshMount" @edit="handleEditMount" @delete="handleDeleteMount" />
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-tab-pane>
 
        <!-- 按类型查看 -->
        <el-tab-pane label="按类型查看" name="by-type">
          <div v-loading="loading" class="tab-content">
            <!-- 下载挂载点 -->
            <div class="type-section">
              <h3 class="type-title">
                <el-icon><Download /></el-icon>
                下载目录
              </h3>
              <MountTable :mounts="downloadMounts" @update="handleUpdateMount" @refresh="handleRefreshMount" @edit="handleEditMount" @delete="handleDeleteMount" />
            </div>
 
            <!-- 媒体库挂载点 -->
            <div class="type-section">
              <h3 class="type-title">
                <el-icon><Film /></el-icon>
                媒体库目录
              </h3>
              <MountTable :mounts="libraryMounts" @update="handleUpdateMount" @refresh="handleRefreshMount" @edit="handleEditMount" @delete="handleDeleteMount" />
            </div>
          </div>
        </el-tab-pane>
 
        <!-- 所有挂载点 -->
        <el-tab-pane label="所有挂载点" name="all">
          <div v-loading="loading" class="tab-content">
            <MountTable :mounts="mounts" @update="handleUpdateMount" @refresh="handleRefreshMount" @edit="handleEditMount" @delete="handleDeleteMount" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 挂载点编辑对话框 -->
    <MountEditDialog
      v-model="editDialogVisible"
      :mount="currentMount"
      @success="loadMounts"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  RefreshRight, FolderOpened, Download, Film, Coin, CircleCheck, Plus
} from '@element-plus/icons-vue'
import {
  getStorageMounts,
  getStorageStats,
  refreshDiskInfo,
  updateStorageMount,
  deleteStorageMount,
  formatSize,
  getSpaceColor,
  type StorageMount,
  type StorageMountUpdate,
  type StorageStatsResponse
} from '@/api/modules/storage'
import MountTable from '@/components/storage/MountTable.vue'
import MountEditDialog from '@/components/storage/MountEditDialog.vue'

// 硬盘图标（Element Plus 没有这个图标，用替代）
const HardDrive = FolderOpened

// 状态
const loading = ref(false)
const refreshing = ref(false)
const activeTab = ref('by-disk')
const expandedDevices = ref<string[]>([])
const mounts = ref<StorageMount[]>([])
const stats = ref<StorageStatsResponse | null>(null)
const editDialogVisible = ref(false)
const currentMount = ref<StorageMount | null>(null)

// 计算属性
const downloadMounts = computed(() => mounts.value.filter(m => m.mount_type === 'download'))
const libraryMounts = computed(() => mounts.value.filter(m => m.mount_type === 'library'))

const groupedByDevice = computed(() => {
  const groups = new Map<string, {
    volume_name: string
    downloadMounts: StorageMount[]
    libraryMounts: StorageMount[]
    total_space: number
    used_space: number
    free_space: number
  }>()

  // 从 host_path 提取 volume 名称（如 /volume4/xxx -> volume4）
  function getVolumeName(hostPath?: string): string {
    if (!hostPath) return '其他'
    // 统一处理斜杠
    const normalizedPath = hostPath.replace(/\\/g, '/')
    
    // 匹配 Windows 盘符 (如 D:/ 或 D:)
    const winMatch = normalizedPath.match(/^([A-Za-z]:)/)
    if (winMatch) return winMatch[1]
    
    // 匹配 /volumeX/ 或 /volumeX 格式
    const match = normalizedPath.match(/^\/(volume\d+)/)
    if (match) return match[1]
    
    // 其他情况返回第一级目录
    const parts = normalizedPath.split('/').filter(Boolean)
    return parts[0] || '其他'
  }

  mounts.value.forEach(mount => {
    const volumeName = getVolumeName(mount.host_path)
    if (!groups.has(volumeName)) {
      groups.set(volumeName, {
        volume_name: volumeName,
        downloadMounts: [],
        libraryMounts: [],
        total_space: 0,
        used_space: 0,
        free_space: 0
      })
    }
    const group = groups.get(volumeName)!
    if (mount.mount_type === 'download') {
      group.downloadMounts.push(mount)
    } else {
      group.libraryMounts.push(mount)
    }
    if (mount.total_space) {
      group.total_space = Math.max(group.total_space, mount.total_space)
      group.used_space = Math.max(group.used_space, mount.used_space || 0)
      group.free_space = Math.max(group.free_space, mount.free_space || 0)
    }
  })

  return Array.from(groups.values()).sort((a, b) => a.volume_name.localeCompare(b.volume_name))
})

// 方法
async function loadMounts() {
  loading.value = true
  try {
    const [mountsRes, statsRes] = await Promise.all([
      getStorageMounts({ is_enabled: false }), // 获取所有，包括禁用的
      getStorageStats()
    ])
    mounts.value = mountsRes.data.items
    stats.value = statsRes.data
    // 默认展开第一个设备
    if (groupedByDevice.value.length > 0 && expandedDevices.value.length === 0) {
      expandedDevices.value = [groupedByDevice.value[0].volume_name]
    }
  } catch (error: any) {
    ElMessage.error('加载挂载点列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function handleRefreshAll() {
  refreshing.value = true
  try {
    const res = await refreshDiskInfo()
    ElMessage.success(`刷新了 ${res.data.count} 个挂载点的磁盘信息`)
    await loadMounts()
  } catch (error: any) {
    ElMessage.error('刷新失败: ' + (error.message || '未知错误'))
  } finally {
    refreshing.value = false
  }
}

async function handleRefreshMount(mountId: number) {
  try {
    await refreshDiskInfo(mountId)
    ElMessage.success('刷新成功')
    await loadMounts()
  } catch (error: any) {
    ElMessage.error('刷新失败: ' + (error.message || '未知错误'))
  }
}

async function handleUpdateMount(mountId: number, data: StorageMountUpdate) {
  try {
    await updateStorageMount(mountId, data)
    ElMessage.success('更新成功')
    await loadMounts()
  } catch (error: any) {
    ElMessage.error('更新失败: ' + (error.message || '未知错误'))
  }
}

function getUsagePercent(used?: number, total?: number): number {
  if (!total || total === 0) return 0
  return Number(((used || 0) / total * 100).toFixed(1))
}

// 添加挂载点
function handleAddMount() {
  currentMount.value = null
  editDialogVisible.value = true
}

// 编辑挂载点
function handleEditMount(mount: StorageMount) {
  currentMount.value = mount
  editDialogVisible.value = true
}

// 删除挂载点
async function handleDeleteMount(mountId: number) {
  try {
    await ElMessageBox.confirm(
      '删除后无法恢复，是否继续？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await deleteStorageMount(mountId)
    ElMessage.success('删除成功')
    await loadMounts()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}



onMounted(() => {
  loadMounts()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.section-description {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.header-right {
  display: flex;
  gap: 12px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
}

.stat-content {
  z-index: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.stat-icon {
  font-size: 48px;
  opacity: 0.15;
  color: var(--el-color-primary);
}

.stat-icon.download { color: #409EFF; }
.stat-icon.library { color: #67C23A; }
.stat-icon.storage { color: #E6A23C; }
.stat-icon.success { color: #67C23A; }

/* 主卡片 */
.main-card {
  margin-bottom: 20px;
}

.tab-content {
  min-height: 300px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

/* 设备分组 */
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 20px;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.device-name {
  font-weight: 600;
  font-size: 15px;
}

.device-space {
  display: flex;
  align-items: center;
  gap: 12px;
}

.space-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

/* 挂载点分组 */
.mount-section {
  margin: 20px 0;
}

.sub-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

/* 类型分组 */
.type-section {
  margin-bottom: 30px;
}

.type-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
